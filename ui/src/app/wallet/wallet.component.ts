import { Component } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
// import * as moment from 'moment';
// import { Observable } from 'rxjs';
// import { QRCodeModule } from 'angularx-qrcode';
import bitcoin from 'bitcoinjs-lib';
import bip39 from 'bip39';
import { fromSeed, BIP32 } from 'bip32';
 
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
    wallet_exists = false;
    mnemonic : string = null;
    saved = false;
    show_mnemonic = false;
    seed : Buffer = null
    node : BIP32;

    constructor(private router: Router, private route: ActivatedRoute) {
        
    }

    createWallet() {
        this.mnemonic = bip39.generateMnemonic()
        this.show_mnemonic = true;
        this.seed = bip39.mnemonicToSeed(this.mnemonic);
        this.node = fromSeed(this.seed, TUXCOIN);
    }

    savedBackupWords() {
        this.wallet_exists = true;
    }

    getAddress(path : string = 'm/0/0') {
        const child = this.node.derivePath(path)
        const { address } = bitcoin.payments.p2wpkh({ pubkey: child.publicKey, network: TUXCOIN});
    }
};

