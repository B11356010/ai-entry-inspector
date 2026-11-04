## 環境安裝與執行

### 1. 安裝 Python

建議使用 Python 3.13，並建立虛擬環境。

### 2. 建立虛擬環境

```bash
py -3.13 -m venv .venv313
```

Windows 啟用虛擬環境：

```powershell
.\.venv313\Scripts\Activate.ps1
```

### 3. 安裝套件

```bash
python -m pip install -r requirements.txt
```

### 4. 檢查 GPU 是否可用

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

若顯示 `True`，代表目前 PyTorch 可以使用 CUDA。

### 5. 啟動系統

```bash
streamlit run app.py
```### 2. 建立虛擬環境

```bash
py -3.13 -m venv .venv313
```

Windows 啟用虛擬環境：

```bash
.venv313\Scripts\activate
```

### 3. 安裝套件

```bash
pip install -r requirements.txt
```

### 4. 檢查 GPU 是否可用

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

若顯示 `True`，代表目前 PyTorch 可以使用 CUDA。

### 5. 啟動系統

```bash
streamlit run app.py
```


