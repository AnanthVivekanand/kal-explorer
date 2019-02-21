import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
// import * as moment from 'moment';
// import { Observable } from 'rxjs';
// import { QRCodeModule } from 'angularx-qrcode';
import bitcoin from 'bitcoinjs-lib';
import bip39 from 'bip39';
import { fromSeed, BIP32 } from 'bip32';
import coinSelect from 'coinselect';
import { WalletService } from './wallet.service';
import * as CryptoJS from 'crypto-js';
import { environment } from '../../environments/environment';
 
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

class Address {
    address : string;
    path: string;
}

@Component({
    templateUrl: './wallet.component.html',
    styleUrls: ['./wallet.component.scss']
})
export class WalletComponent implements OnInit {
    title = 'Address';
    wallet_import = false;
    wallet_create = false;
    mnemonic : string = null;
    saved = false;
    show_mnemonic = false;
    seed : Buffer = null
    wallet : BIP32;
    addresses : Address[] = [];
    mnemonic_valid = null;
    balance : number = 0;
    send_address : string;
    send_amount : number;
    send_message : string;
    environment = environment;
    log : string[] = [];

    constructor(private router: Router, private route: ActivatedRoute, private walletService : WalletService) {
        
    }

    ngOnInit() {
        this.mnemonic = this.getMnemonic();
        this.doImport();
    }

    reset() {
        this.wallet = null;
        this.seed = null;
        this.mnemonic = null;
        this.wallet_import = false;
        this.wallet_create = false;
        this.saved = false;
        this.show_mnemonic = false;
        this.addresses = [];
        this.mnemonic_valid = null;
        this.balance = 0;
        this.send_address = null;
        this.send_amount = null;
    }

    logout() {
        this.clearMnemonic();
        this.reset();
    }

    clearMnemonic() {
        localStorage.removeItem('mnemonic');
    }

    getMnemonic() : string {
        const cipherText = localStorage.getItem('mnemonic')
        const bytes = CryptoJS.AES.decrypt(cipherText, 'key');
        return bytes.toString(CryptoJS.enc.Utf8)
    }

    setMnemonic(mnemonic : string) {
        const cipherText = CryptoJS.AES.encrypt(mnemonic, 'key').toString();
        localStorage.setItem('mnemonic', cipherText);
    }

    createWallet() {
        this.wallet_create = true;
        this.mnemonic = bip39.generateMnemonic();
        this.setMnemonic(this.mnemonic);
        this.show_mnemonic = true;
        this.seed = bip39.mnemonicToSeed(this.mnemonic);
    }

    importWallet() {
        this.wallet_import = true;
    }

    savedBackupWords() {
        this.wallet = fromSeed(this.seed, TUXCOIN);
        this.loadWallet();
    }

    doImport() {
        this.mnemonic_valid = bip39.validateMnemonic(this.mnemonic);
        this.seed = bip39.mnemonicToSeed(this.mnemonic);
        this.setMnemonic(this.mnemonic);
        this.wallet = fromSeed(this.seed, TUXCOIN);
        this.loadWallet();
    }

    loadWallet() {
        let address = this.getAddress();
        this.addresses.push(address);
        address = this.getChangeAddress();
        this.addresses.push(address);
        this.updateBalance();
    }

    getAddress(path : string = 'm/0/0') : any {
        const child = this.wallet.derivePath(path)
        const { address } = bitcoin.payments.p2wpkh({ pubkey: child.publicKey, network: TUXCOIN});
        return {
            path,
            address
        };
    }

    async updateBalance() {
        let _balance = 0;
        for(let address of this.addresses) {
            const res = await this.walletService.getBalance(address.address);
            _balance += res.balance;
        }
        this.balance = _balance;
    }

    getChangeAddress(path : string = 'm/1/0') : any {
        return this.getAddress(path);
    }

    async _getUtxos() {
        const utxos = []
        for(let address of this.addresses){
            const _utxos = await this.walletService.getUtxos(address.address);
            for(let u of _utxos){
                utxos.push({
                    'txid': u.txid,
                    'vout': parseInt(u.vout),
                    'value': u.amount,
                    'scriptPubKey': u.scriptPubKey,
                    'path': address.path,
                });
            } 
        }
        return utxos;
    }

    async sendMessage() {
        const utxos = await this._getUtxos();
        console.log(utxos);
        const targets = [{
            'address': this.addresses[0].address,
            'value': 0.01 * environment.coin.division,
        }];
        let feeRate = 700; // satoshis per byte
        let { inputs, outputs, fee } = coinSelect(utxos, targets, feeRate)

        if (!inputs || !outputs) {
            console.log(inputs, outputs);
            return;
        }

        let txb = new bitcoin.TransactionBuilder(TUXCOIN);

        inputs.forEach(input => {
            console.log('Adding input', input);
            txb.addInput(input.txid, input.vout, null, Buffer.from(input.scriptPubKey, 'hex'))
        });
        outputs.forEach(output => {
            if (!output.address) {
                output.address = this.getChangeAddress().address;
                txb.addOutput(output.address, output.value)
                console.log('Adding change output', output);
                return;
            }
            console.log('Adding output', output);
            // txb.addOutput(output.address, output.value)
            const data = Buffer.concat([Buffer.from('feab', 'hex'), Buffer.from(this.send_message, 'utf8')]);
            const embed = bitcoin.payments.embed({ data: [data] })
            // txb.addInput(unspent.txId, unspent.vout)
            txb.addOutput(embed.output, output.value)
        });
        inputs.forEach((input, i) => {
            console.log('Signing utxo', i, input);
            txb.sign(i, this.wallet.derivePath(input.path), null, null, input.value)
        });
        // txb.sign(0, this.wallet.derivePath('m/0/0'), null, null, inputs[0].value)
        const built = txb.build();
        const hex = built.toHex();

        const tx = bitcoin.Transaction.fromHex(hex);

        console.log(tx.outs);
        tx.outs.forEach((out, i) => {
            try{
                this.log.push(`Will send ${out.value} to ` + bitcoin.address.fromOutputScript(out.script, TUXCOIN));
            }catch(e){
                this.log.push(`Msg tx`);
            }
        })
        this.log.push(`Fee is ${fee}`);
        this.log.push(`Signed tx: ${hex}`);
        this.walletService.broadcast(hex);
        this.log.push(`Transaction has been broadcast ${built.getId()}`);
    }

    async send() {
        const utxos = await this._getUtxos();
        console.log(utxos);
        const targets = [{
            'address': this.send_address,
            'value': this.send_amount * environment.coin.division,
        }];
        let feeRate = 700; // satoshis per byte
        let { inputs, outputs, fee } = coinSelect(utxos, targets, feeRate)

        if (!inputs || !outputs) {
            console.log(inputs, outputs);
            return;
        }

        let txb = new bitcoin.TransactionBuilder(TUXCOIN);

        inputs.forEach(input => {
            console.log('Adding input', input);
            txb.addInput(input.txid, input.vout, null, Buffer.from(input.scriptPubKey, 'hex'))
        });
        outputs.forEach(output => {
            if (!output.address) {
                output.address = this.getChangeAddress().address;
            }
            console.log('Adding output', output);
            txb.addOutput(output.address, output.value)
        });
        inputs.forEach((input, i) => {
            console.log('Signing utxo', i, input);
            txb.sign(i, this.wallet.derivePath(input.path), null, null, input.value)
        });
        // txb.sign(0, this.wallet.derivePath('m/0/0'), null, null, inputs[0].value)
        const built = txb.build();
        const hex = built.toHex();

        const tx = bitcoin.Transaction.fromHex(hex);

        console.log(tx.outs);
        tx.outs.forEach((out, i) => {
            this.log.push(`Will send ${out.value} to ` + bitcoin.address.fromOutputScript(out.script, TUXCOIN));
        })
        this.log.push(`Fee is ${fee}`);
        this.log.push(`Signed tx: ${hex}`);
        this.walletService.broadcast(hex);
        this.log.push(`Transaction has been broadcast ${built.getId()}`);
    }
};

