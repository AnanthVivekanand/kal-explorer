import { Component } from '@angular/core';
import {Router} from "@angular/router";
import { AddressService } from './address.service';

@Component({
  templateUrl: './richlist.component.html',
//   styleUrls: ['./home.component.scss']
})
export class RichListComponent {
  title = 'Rich List';
  richlist : any [];

  constructor(private router : Router, private addressService : AddressService) {
    this.addressService.getRichList().then(data => {
        this.richlist = data;
    });
  }

  goAddress(addr : String) {
    this.router.navigate(['address', addr]);
  }
};

