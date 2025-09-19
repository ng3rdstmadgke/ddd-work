
```bash
./bin/mysql.sh

# 作成
poetry run python 08_architecture/db/create_all.py

# 削除
poetry run python 08_architecture/db/drop_all.py
```

ログイン

```bash
MYSQL_PWD=root1234 mysql -u root -h 127.0.0.1 -P 3306 sample
```