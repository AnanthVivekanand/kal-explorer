import { Component } from '@angular/core';
import { BlocksService } from './blocks.service';
import {Router} from "@angular/router";
import * as moment from 'moment';
import { Title }  from '@angular/platform-browser';
import { TransactionService } from './transactions.service';
import { environment } from '../environments/environment';
import { VERSION } from '../environments/version';

@Component({
  selector: 'home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  title = 'ui';
  blocks : any [] = [];
  transactions : any [] = [];
  environment = environment;
  version = VERSION;

  constructor(private router : Router, blocksService : BlocksService, private txService : TransactionService, private titleService : Title) {
    blocksService.getBlocks(10)
    .subscribe((data: [any]) => this.blocks = data)
    this.titleService.setTitle('Home | Explorer')
    // this.statusService.currentStatus.subscribe((data: [any]) => this.status = data)

    txService.txObservable.subscribe((data : any) => {
      if(!data){
        return;
      }
      this.transactions.unshift(data);
      this.transactions = this.transactions.slice(0, 10);
    })

    blocksService.blocksObservable.subscribe((data: any) => {
      if(!data) {
        return;
      }
      this.blocks.unshift(data);
      this.blocks = this.blocks.slice(0, 10);
    });
  }

  goBlock(blockhash : String) {
    this.router.navigate(['block', blockhash]);
  }

  goTx(txid : String) {
    this.router.navigate(['tx', txid]);
  }

  age(time : number) {
    return moment(time*1000).fromNow()
  }
};

