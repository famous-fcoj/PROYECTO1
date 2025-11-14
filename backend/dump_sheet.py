import pandas as pd
path = r"c:\Users\$$$$$$$$$$$$$$$$$$$$\Desktop\PROYECTO1\OT 2025 MECANICAS.xlsx"
xls = pd.ExcelFile(path)
sheet = xls.sheet_names[0]
print('Dumping sheet:', sheet)
df = xls.parse(sheet_name=sheet, header=None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
print(df.iloc[:40,:10].to_string(index=True, header=False))
