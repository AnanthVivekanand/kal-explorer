import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AddressService } from './address.service';
import { TransactionService } from './transactions.service';
import * as moment from 'moment';
import { Observable } from 'rxjs';
import { Title }  from '@angular/platform-browser';


@Component({
    templateUrl: './transaction.component.html',
    // styleUrls: ['./address.component.scss']
})
export class TransactionComponent implements OnInit {
    txid: string;
    tx: any;

    constructor(private router: Router, private route: ActivatedRoute, private txService: TransactionService, private titleService : Title) {

    }

    ngOnInit() {
        this.route.params.subscribe(params => {
            this.txid = params['txid'];
            this.titleService.setTitle(this.txid);
            this.txService.getTransaction(this.txid).then(data => {
                this.tx = data;
            })
        });
    }

    timestamp() {
        //Jan 31, 2019 8:20:36 PM
        return moment(this.tx.timestamp*1000).format('MMM DD, YYYY H:mm:ss');
    }

    goBlock(blockhash : String) {
        this.router.navigate(['block', blockhash])
    }

};

