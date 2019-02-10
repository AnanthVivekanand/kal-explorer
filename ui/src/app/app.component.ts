import { Component, OnInit } from '@angular/core';
import { StatusService } from './status.service';
import { BlocksService } from './blocks.service';
import { AddressService } from './address.service';
import { TransactionService } from './transactions.service';
import {Router} from '@angular/router';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  title = 'Explorer';
  status : any = {};
  search_text : string = null;

  constructor(private router : Router, private statusService : StatusService, private blockService : BlocksService, private addressService : AddressService, private txService : TransactionService){ }

  ngOnInit() {
    this.statusService.currentStatus.subscribe((data: [any]) => this.status = data)
    this.statusService.updateStatus();
  }

  goHome() {
    this.router.navigate([''])
  }

  goBlocks() {

  }

  goWallet() {
    this.router.navigate(['wallet'])
  }

  goRichList() {
    this.router.navigate(['richlist'])
  }

  async doSearch() {
    // 1. Block
    // 2. TX
    // 3. Address
    // 4. Block height (height returns hash)
    try{
      const block : any = await this.blockService.getBlock(this.search_text).toPromise();
      this.router.navigate(['block', block.hash]);
    }catch(e) {
      try{
        const tx : any = await this.txService.getTransaction(this.search_text);
        this.router.navigate(['tx', tx.txid]);
      }catch(e){
          const address : any = await this.addressService.getBalance(this.search_text);
          this.router.navigate(['address', this.search_text]);
      }
    }
  }

}
