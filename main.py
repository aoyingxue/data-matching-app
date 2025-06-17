import streamlit as st
import pandas as pd

st.set_page_config(page_title="Master Data Matching Tool", layout="wide")
st.title("Master Data Matching Tool")

# 上传文件
st.sidebar.header("Upload Files")
uploader_raw = st.sidebar.file_uploader("Upload raw data", type=["csv", "xlsx", "json"])
uploader_ref = st.sidebar.file_uploader("Upload reference mapping", type=["csv", "xlsx", "json"])

if uploader_raw and uploader_ref:
    # 读取原始数据
    if uploader_raw.name.endswith(".xlsx"):
        df_raw = pd.read_excel(uploader_raw, sheet_name=None)
        if len(df_raw) > 1:
            sheet_raw = st.sidebar.selectbox("Select sheet from raw data", options=list(df_raw.keys()))
            df_raw = df_raw[sheet_raw]
        else:
            df_raw = list(df_raw.values())[0]
    elif uploader_raw.name.endswith(".json"):
        df_raw = pd.read_json(uploader_raw)
        # 添加JSON数据切换选项
        if st.sidebar.checkbox("Transpose Raw Data JSON (switch rows and columns)", key="transpose_raw"):
            df_raw = df_raw.transpose()
    else:
        df_raw = pd.read_csv(uploader_raw)

    # 读取参考数据
    if uploader_ref.name.endswith(".xlsx"):
        df_ref = pd.read_excel(uploader_ref, sheet_name=None)
        if len(df_ref) > 1:
            sheet_ref = st.sidebar.selectbox("Select sheet from reference data", options=list(df_ref.keys()))
            df_ref = df_ref[sheet_ref]
        else:
            df_ref = list(df_ref.values())[0]
    elif uploader_ref.name.endswith(".json"):
        df_ref = pd.read_json(uploader_ref)
        # 添加JSON数据切换选项
        if st.sidebar.checkbox("Transpose Reference Data JSON (switch rows and columns)", key="transpose_ref"):
            df_ref = df_ref.transpose()
    else:
        df_ref = pd.read_csv(uploader_ref)

    st.sidebar.success("Files uploaded.")

    # 添加数据预览部分
    st.subheader("Data Preview")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Raw Data Preview:")
        st.dataframe(
            df_raw.head(),
            use_container_width=True,
            height=300
        )
        st.write(f"Raw Data Shape: {df_raw.shape}")
    
    with col2:
        st.write("Reference Data Preview:")
        st.dataframe(
            df_ref.head(),
            use_container_width=True,
            height=300
        )
        st.write(f"Reference Data Shape: {df_ref.shape}")

    st.subheader("Select columns for matching")
    raw_cols = st.multiselect("Select column(s) from raw data to match", df_raw.columns)
    ref_cols = st.multiselect("Select column(s) from reference data as key", df_ref.columns)
    # 排除已经在ref_cols中选中的列
    available_ref_cols = [col for col in df_ref.columns if col not in ref_cols]
    ref_value_cols = st.multiselect("Select calibrated value column(s) from reference data", available_ref_cols)
    
    # 选择校准后的列名
    st.subheader("Configure Output Columns")
    output_config = []
    for ref_col in ref_value_cols:
        st.write(f"---")
        st.write(f"**Configuration for {ref_col}**")
        col1, col2, col3 = st.columns(3)
        with col1:
            # 选择是否替换现有列
            replace_existing = st.checkbox(f"Replace existing column", key=f"replace_{ref_col}")
        with col2:
            if replace_existing:
                # 如果替换现有列，选择要替换的列
                if len(raw_cols) == 1:
                    # 如果只有一列可选，直接使用该列
                    replace_col = raw_cols[0]
                    st.write(f"Column to replace: {replace_col}")
                else:
                    # 如果有多列可选，显示选择框
                    replace_col = st.selectbox(f"Select column to replace", raw_cols, key=f"replace_col_{ref_col}")
                # 选择是否保留原数据
                keep_original = st.checkbox(f"Keep original data as new column", key=f"keep_original_{ref_col}")
                original_col_name = None  # 初始化为None
                if keep_original:
                    original_col_name = st.text_input(f"Name for original data column", 
                                                    value=f"{replace_col}_original",
                                                    key=f"original_col_name_{ref_col}")
                    if not original_col_name or not original_col_name.strip():  # 如果用户输入为空，使用默认值
                        original_col_name = f"{replace_col}_original"
                output_config.append({
                    "ref_col": ref_col, 
                    "replace_col": replace_col, 
                    "is_new": False,
                    "keep_original": keep_original,
                    "original_col_name": original_col_name if keep_original else None
                })
            else:
                # 如果是新列，输入列名
                new_col_name = st.text_input(f"Enter new column name", key=f"new_col_{ref_col}")
                if new_col_name and new_col_name.strip():  # 确保列名不为空
                    output_config.append({
                        "ref_col": ref_col, 
                        "new_col": new_col_name.strip(), 
                        "is_new": True,
                        "keep_original": False
                    })

    if raw_cols and ref_cols and ref_value_cols and output_config:
        # 创建匹配key列
        df_raw["__merge_key__"] = df_raw[raw_cols].astype(str).agg(" | ".join, axis=1)
        df_ref["__merge_key__"] = df_ref[ref_cols].astype(str).agg(" | ".join, axis=1)

        # 创建映射字典
        mapping_dict = {}
        for _, row in df_ref.iterrows():
            mapping_dict[row["__merge_key__"]] = {col: row[col] for col in ref_value_cols}

        # 创建一个新的DataFrame来存储结果
        result_df = df_raw.copy()

        # 应用校准值
        for config in output_config:
            if config["is_new"]:
                # 添加新列
                result_df[config["new_col"]] = result_df["__merge_key__"].map(lambda x: mapping_dict.get(x, {}).get(config["ref_col"]))
            else:
                # 如果需要保留原数据，先保存
                if config.get("keep_original") and config.get("original_col_name"):
                    result_df[config["original_col_name"]] = result_df[config["replace_col"]].copy()
                # 替换现有列
                result_df[config["replace_col"]] = result_df["__merge_key__"].map(lambda x: mapping_dict.get(x, {}).get(config["ref_col"]))

        # 找出未匹配项
        st.subheader("Manual Matching for Unmapped Keys")
        # 获取未匹配项的所有原始列数据
        unmatched_mask = pd.Series(False, index=result_df.index)
        for config in output_config:
            if config["is_new"]:
                unmatched_mask |= result_df[config["new_col"]].isna()
            else:
                unmatched_mask |= result_df[config["replace_col"]].isna()
        
        df_unmatched = result_df[unmatched_mask][raw_cols + ["__merge_key__"]].drop_duplicates()
        
        if not df_unmatched.empty:
            # 创建用于手动映射的表格
            manual_mapping_data = []
            for _, row in df_unmatched.iterrows():
                mapping_row = {
                    "Original Value": row["__merge_key__"],
                }
                # 添加所有用于匹配的原始列
                for col in raw_cols:
                    mapping_row[f"Original {col}"] = row[col]
                # 添加所有校准值列
                for ref_col in ref_value_cols:
                    mapping_row[f"Calibrated {ref_col}"] = ""
                manual_mapping_data.append(mapping_row)
            
            manual_mapping_df = pd.DataFrame(manual_mapping_data)
            
            # 重新排序列
            column_order = ["Original Value"] + [f"Original {col}" for col in raw_cols] + [f"Calibrated {col}" for col in ref_value_cols]
            manual_mapping_df = manual_mapping_df[column_order]
            
            # 使用可编辑表格
            edited_mapping = st.data_editor(
                manual_mapping_df,
                use_container_width=True,
                height=min(300, 35 + len(manual_mapping_df) * 35),
                num_rows="dynamic",
                key="manual_mapping_editor",
                column_config={
                    "Original Value": st.column_config.TextColumn(
                        "Original Value",
                        disabled=True
                    ),
                    **{f"Original {col}": st.column_config.TextColumn(
                        f"Original {col}",
                        disabled=True
                    ) for col in raw_cols},
                    **{f"Calibrated {col}": st.column_config.TextColumn(
                        f"Calibrated {col}",
                        help=f"Enter the calibrated value for {col}"
                    ) for col in ref_value_cols}
                }
            )
            
            # 更新手动映射
            for _, row in edited_mapping.iterrows():
                for ref_col in ref_value_cols:
                    if row[f"Calibrated {ref_col}"]:  # 只处理有值的行
                        mapping_dict[row["Original Value"]] = mapping_dict.get(row["Original Value"], {})
                        mapping_dict[row["Original Value"]][ref_col] = row[f"Calibrated {ref_col}"]
                        # 更新result_df中的相应列
                        for config in output_config:
                            if config["ref_col"] == ref_col:
                                if config["is_new"]:
                                    result_df.loc[result_df["__merge_key__"] == row["Original Value"], config["new_col"]] = row[f"Calibrated {ref_col}"]
                                else:
                                    result_df.loc[result_df["__merge_key__"] == row["Original Value"], config["replace_col"]] = row[f"Calibrated {ref_col}"]
        else:
            st.success("No unmatched items found!")

        st.success("Matching complete")

        # 显示可编辑的映射预览
        st.subheader("Mapping Preview (Editable)")
        preview_df = pd.DataFrame({
            "Original Value": list(mapping_dict.keys()),
            **{f"Calibrated {col}": [mapping_dict[k].get(col) for k in mapping_dict.keys()] for col in ref_value_cols}
        })
        
        # 使用st.data_editor创建可编辑表格
        edited_df = st.data_editor(
            preview_df,
            use_container_width=True,
            height=min(400, 35 + len(preview_df) * 35),
            num_rows="dynamic",
            key="mapping_editor"
        )
        
        # 更新映射关系
        if edited_df is not None:
            for ref_col in ref_value_cols:
                for _, row in edited_df.iterrows():
                    if row[f"Calibrated {ref_col}"]:  # 只处理有值的行
                        mapping_dict[row["Original Value"]] = mapping_dict.get(row["Original Value"], {})
                        mapping_dict[row["Original Value"]][ref_col] = row[f"Calibrated {ref_col}"]
                        # 更新result_df中的相应列
                        for config in output_config:
                            if config["ref_col"] == ref_col:
                                if config["is_new"]:
                                    result_df.loc[result_df["__merge_key__"] == row["Original Value"], config["new_col"]] = row[f"Calibrated {ref_col}"]
                                else:
                                    result_df.loc[result_df["__merge_key__"] == row["Original Value"], config["replace_col"]] = row[f"Calibrated {ref_col}"]

        # 删除所有临时列
        result_df = result_df.drop(columns=["__merge_key__"])

        # 下载最终结果
        st.subheader("Download")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Calibrated Data (CSV)", 
                result_df.to_csv(index=False, encoding='utf-8-sig'), 
                file_name="calibrated_data.csv",
                mime="text/csv"
            )
        with col2:
            # 创建一个Excel writer对象
            buffer = pd.ExcelWriter("calibrated_data.xlsx", engine='openpyxl')
            result_df.to_excel(buffer, index=False, sheet_name='Calibrated Data')
            buffer.close()
            with open("calibrated_data.xlsx", "rb") as f:
                st.download_button(
                    "Download Calibrated Data (Excel)", 
                    f.read(), 
                    file_name="calibrated_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        # 创建更新后的映射文件
        updated_mapping = pd.DataFrame({
            "Original": list(mapping_dict.keys()),
            **{f"Calibrated_{col}": [mapping_dict[k].get(col) for k in mapping_dict.keys()] for col in ref_value_cols}
        }).drop_duplicates()

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Updated Reference Mapping (CSV)", 
                updated_mapping.to_csv(index=False, encoding='utf-8-sig'), 
                file_name="updated_mapping.csv",
                mime="text/csv"
            )
        with col2:
            # 创建一个Excel writer对象
            buffer = pd.ExcelWriter("updated_mapping.xlsx", engine='openpyxl')
            updated_mapping.to_excel(buffer, index=False, sheet_name='Updated Mapping')
            buffer.close()
            with open("updated_mapping.xlsx", "rb") as f:
                st.download_button(
                    "Download Updated Reference Mapping (Excel)", 
                    f.read(), 
                    file_name="updated_mapping.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
else:
    st.warning("Please upload both raw data and reference mapping file.")

# 在文档最后添加使用说明
st.markdown("---")  # 添加分隔线
st.markdown("""
### 📝 How to Use This Tool

1. **Upload Files**
   - Upload your raw data file (CSV or Excel)
   - Upload your reference mapping file (CSV or Excel)

2. **Select Columns**
   - Choose one or more columns from raw data that need to be matched
   - Select corresponding key columns from reference data
   - Pick a column from reference data that contains the calibrated values

3. **Manual Mapping**
   - For any unmatched items, you can manually enter the correct mapping
   - The tool will remember your manual mappings

4. **Edit & Review**
   - Review all mappings in the editable table
   - Make direct edits to the calibrated values if needed
   - Add or remove mappings as required

5. **Download Results**
   - Download the calibrated data with updated values
   - Download the updated reference mapping for future use

> 💡 **Tip**: You can edit the mapping table directly to make quick adjustments to your mappings.
""")
