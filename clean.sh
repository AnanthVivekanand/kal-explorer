docker exec -it postgres psql -U postgres tuxcoin -c "DROP TABLE block; DROP TABLE transaction; DROP TABLE address; DROP TABLE addresschanges; DROP TABLE utxo; DROP TABLE message;"

rm -r data/blocks.dat
rm -r chainstate
