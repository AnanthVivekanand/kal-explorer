import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AddressService } from './address.service';
import { TransactionComponent } from './transaction.component';
import * as moment from 'moment';
import { Observable } from 'rxjs';


@Component({
    selector: 'address',
    templateUrl: './address.component.html',
    styleUrls: ['./address.component.scss']
})
export class AddressComponent implements OnInit {
    title = 'Address';
    balance: Number;
    sub : any;
    address : string;

    constructor(private router : Router, private route: ActivatedRoute, private addressService: AddressService) {
        
    }

    ngOnInit() {
        this.sub = this.route.params.subscribe(params => {
            this.address = params['address'];
            this.addressService.getBalance(this.address).then(data => { 
                this.balance = data.balance / 100000000;
            });
          });
    }

};

