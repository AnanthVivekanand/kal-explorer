import { Component } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
// import * as moment from 'moment';
// import { Observable } from 'rxjs';
// import { QRCodeModule } from 'angularx-qrcode';
import bitcoin from 'bitcoinjs-lib';
import bip39 from 'bip39';
import { fromSeed, BIP32 } from 'bip32';
import coinSelect from 'coinselect';
import { WalletService } from './wallet.service';
 
const TUXCOIN = {
    messagePrefix: '\x19Tuxcoin Signed Message:\n',
    bip32: {
        public: 0x0488ADE4,
        private: 0x0488B21E
    },
    bech32: 'tux',
    pubKeyHash: 0x41,
    scriptHash: 0x40,
    wif: 0xc1
}

@Component({
    templateUrl: './wallet.component.html',
    // styleUrls: ['./address.component.scss']
})
export class WalletComponent {
    title = 'Address';
    wallet_import = false;
    wallet_create = false;
    mnemonic : string = null;
    saved = false;
    show_mnemonic = false;
    import_wallet = false;
    seed : Buffer = null
    wallet : BIP32;
    addresses : string[] = [];
    mnemonic_valid = null;
    balance : number = 0;
    send_address : string;
    send_amount : number;

    constructor(private router: Router, private route: ActivatedRoute, private walletService : WalletService) {
        
    }

    createWallet() {
        this.wallet_create = true;
        this.mnemonic = bip39.generateMnemonic()
        this.show_mnemonic = true;
        this.seed = bip39.mnemonicToSeed(this.mnemonic);
    }

    importWallet() {
        this.wallet_import = true;
    }

    savedBackupWords() {
        this.wallet = fromSeed(this.seed, TUXCOIN);
        this.getAddress();
    }

    doImport() {
        this.mnemonic_valid = bip39.validateMnemonic(this.mnemonic);
        this.seed = bip39.mnemonicToSeed(this.mnemonic);
        this.wallet = fromSeed(this.seed, TUXCOIN);
        this.getAddress();
    }

    getAddress(path : string = 'm/0/0') {
        const child = this.wallet.derivePath(path)
        const { address } = bitcoin.payments.p2wpkh({ pubkey: child.publicKey, network: TUXCOIN});
        this.addresses.push(address);
        this.updateBalance();
    }

    async updateBalance() {
        for(let address of this.addresses) {
            const res = await this.walletService.getBalance(address);
            this.balance += res.balance;
        }
    }

    getChangeAddress(path : string = 'm/1/0') : string {
        const child = this.wallet.derivePath(path)
        const { address } = bitcoin.payments.p2wpkh({ pubkey: child.publicKey, network: TUXCOIN});
        return address;
    }

    async send() {
        const _utxos = await this.walletService.getUtxos(this.addresses[0]);
        const utxos = []
        for(let u of _utxos){
            utxos.push({
                'txid': u.txid,
                'vout': parseInt(u.vout),
                'value': u.amount,
                'scriptPubKey': u.scriptPubKey
            });
        }
        const targets = [{
            'address': this.send_address,
            'value': this.send_amount,
        }];
        console.log(utxos, targets);
        let feeRate = 700; // satoshis per byte
        let { inputs, outputs, fee } = coinSelect(utxos, targets, feeRate)

        console.log(inputs, outputs, fee)

        if (!inputs || !outputs) return

        let txb = new bitcoin.TransactionBuilder(TUXCOIN);

        inputs.forEach(input => txb.addInput(input.txid, input.vout, null, Buffer.from(input.scriptPubKey, 'hex')))
        outputs.forEach(output => {
            if (!output.address) {
                output.address = this.getChangeAddress();
            }

            txb.addOutput(output.address, output.value)
        });
        txb.sign(0, this.wallet.derivePath('m/0/0'), null, null, inputs[0].value)
        console.log(txb.build().toHex());
    }

    test(){
        let feeRate = 55 // satoshis per byte
        let utxos = [
        {
            txId: '96568edf8b9b847e1cf5429101fbef8ac2901224b64c22bd412bd32ae1f61bcf',
            vout: 0,
            value: 1000000
        }
        ]
        let targets = [
        {
            address: 'TBurnerEUjv3LGZ1r2MW1cE2Nrg4GKVD7x',
            value: 5000
        }
        ]

        // ...
        let { inputs, outputs, fee } = coinSelect(utxos, targets, feeRate)

        // the accumulated fee is always returned for analysis
        console.log(fee)

        // .inputs and .outputs will be undefined if no solution was found
        if (!inputs || !outputs) return

        let txb = new bitcoin.TransactionBuilder(TUXCOIN);

        inputs.forEach(input => txb.addInput(input.txId, input.vout))
        outputs.forEach(output => {
            // watch out, outputs may have been added that you need to provide
            // an output address/script for
            if (!output.address) {
                output.address = this.getChangeAddress();
            }

            txb.addOutput(output.address, output.value)
        })
    }
};

