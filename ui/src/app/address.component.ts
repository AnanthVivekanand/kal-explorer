import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AddressService } from './address.service';
import { TransactionService } from './transactions.service';
import * as moment from 'moment';
import { Observable } from 'rxjs';
// import { QRCodeModule } from 'angularx-qrcode';


@Component({
    selector: 'address',
    templateUrl: './address.component.html',
    styleUrls: ['./address.component.scss']
})
export class AddressComponent implements OnInit {
    title = 'Address';
    balance: Number;
    sub: any;
    address: string;
    txs : any[] = [];

    sum = 100;
    throttle = 300;
    scrollDistance = 1;
    scrollUpDistance = 2;

    lastTime : Number;

    constructor(private router: Router, private route: ActivatedRoute, private addressService: AddressService, private txService: TransactionService) {

    }

    onScrollDown() {
        console.log('add more');
        this.moreTxs();
    }

    ngOnInit() {
        this.route.params.subscribe(params => {
            this.address = params['address'];
            this.addressService.getBalance(this.address).then(data => {
                this.balance = data.balance / 100000000;
            });
            this.moreTxs();
        });
    }

    moreTxs() {
        this.txService.getTransactions(this.address, this.lastTime).then(data => {
            if(data.length === 0){
                return;
            }
            for(let tx of data.txs){
                this.txs.push(tx);
            }
            this.lastTime = data.lastTime;
        });
    }

};

