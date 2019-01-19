# Kryptonite explorer

## Data directories

PostgreSQL and LevelDB is used for this explorer. 

PostgreSQL provides analytical capabilities and is what powers the frontend and APIs. LevelDB is needed to track chainstate such as UTXOs and spent values, LevelDB as it is much faster than PostgreSQL.