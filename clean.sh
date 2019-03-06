docker exec -it postgres psql -U postgres explorer_tux -c "DROP TABLE block; DROP TABLE transaction; DROP TABLE address; DROP TABLE addresschanges; DROP TABLE utxo; DROP TABLE message; DROP TABLE walletgroup; DROP TABLE walletgroupaddress"

rm -r /data/explorer/
