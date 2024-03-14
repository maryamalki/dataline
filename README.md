# DataLine

## Running

To run DataLine, you can use our official docker image:
```docker run ramiawar/dataline -p 2222:2222 -p 7377:7377```



### ⚠️ Connecting to the database

Make sure to add the 'connector' to your database connection string. 

If using Postgres, please use psycopg2:

```bash
postgresql+psycopg2://postgres:secret@localhost:5432/adventureworks
```

For MySQL, please use pymysql:
```bash
mysql+pymysql://root@localhost:3306/mydatabase
```
