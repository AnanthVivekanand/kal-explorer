import { Component, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import * as moment from 'moment';
import { text } from '@angular/core/src/render3';


@Component({
    selector: 'transaction',
    templateUrl: './transaction.component.html',
    styleUrls: ['./transaction.component.scss']
})
export class TransactionBlockComponent implements OnInit {
    @Input() tx : any;
    keys_in : string[];
    keys_out : string[];

    constructor(private router : Router) {
        
    };

    ngOnInit() {
        this.keys_out = Object.keys(this.tx.addresses_out);
        this.keys_in = Object.keys(this.tx.addresses_in);
    }

    timestamp() {
        //Jan 31, 2019 8:20:36 PM
        return moment(this.tx.timestamp*1000).format('MMM DD, YYYY H:mm:ss');
    }

    is_coinbase() {
        const keys = Object.keys(this.tx.addresses_in);
        // console.log('length: ' + (this.tx.addresses_in.length == 1));
        // console.log('keys: ' + (Object.keys(this.tx.addresses_in)[0] === 'null'));
        return keys.length === 1 && (Object.keys(this.tx.addresses_in)[0] === 'null');
    }

    parse_value(value) {
        return value / 100000000;
    }

    goAddress(addr : string) {
        this.router.navigate(['address', addr])
    }
};

