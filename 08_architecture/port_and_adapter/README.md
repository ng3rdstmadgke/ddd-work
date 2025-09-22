
```bash
./bin/mysql.sh

# 作成
poetry run python 08_architecture/port_and_adapter/create_all.py

# 削除
poetry run python 08_architecture/port_and_adapter/drop_all.py
```

ログイン

```bash
MYSQL_PWD=root1234 mysql -u root -h 127.0.0.1 -P 3306 sample -e "SHOW TABLES;"
```

app

```bash
(cd 08_architecture/port_and_adapter && poetry run uvicorn app:app --reload)
```

- http://localhost:8000/docs