import { Component } from '@angular/core';
import { BlocksService } from './blocks.service';
import {Router} from "@angular/router";
import * as moment from 'moment';
import { Title }  from '@angular/platform-browser';


@Component({
  selector: 'home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  title = 'ui';
  blocks : any [];

  constructor(private router : Router, blocksService : BlocksService, private titleService : Title) {
    blocksService.getBlocks()
    .subscribe((data: [any]) => this.blocks = data)
    this.titleService.setTitle('Home | Explorer')
  }

  goBlock(blockhash : String) {
    this.router.navigate(['block', blockhash]);
  }

  age(time : number) {
    return moment(time*1000).fromNow()
  }
};

