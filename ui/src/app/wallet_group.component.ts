import { Component } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AddressService } from './address.service';
import { Title } from '@angular/platform-browser';
import { environment } from '../environments/environment';


@Component({
    templateUrl: './wallet_group.component.html',
})
export class WalletGroupComponent {
    title = 'Wallet';
    walletId : string;
    addresses : string[];
    environment = environment;

    constructor(private router: Router,
        private route: ActivatedRoute,
        private addressService: AddressService, 
        private titleService: Title) {

        titleService.setTitle('Wallet');    
        this.route.params.subscribe(params => {
            this.walletId = params['walletId'];
            this.addressService.getWallet(this.walletId).then(res => {
                this.addresses = res.addresses;
            });
        });
    }

    goAddress(addr: string) {
        this.router.navigate(['address', addr]);
    }
};

