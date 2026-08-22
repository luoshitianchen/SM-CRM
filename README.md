# SM CRM

客户关系管理：客户、商机、合同、回款和客户服务。

```powershell
git clone https://github.com/luoshitianchen/SM-CRM.git
cd SM-CRM
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8510
```

接口：`/health`、`/readyz`、`/api/overview`、`/api/items`、`/api/ops/metrics`、`/api/crypto/status`。
