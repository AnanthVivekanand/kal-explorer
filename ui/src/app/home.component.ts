import { Component } from '@angular/core';
import { BlocksService } from './blocks.service';
import * as moment from 'moment';


@Component({
  selector: 'home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  title = 'ui';
  blocks : any [];

  constructor(blocksService : BlocksService) {
    blocksService.getBlocks()
    .subscribe((data: [any]) => this.blocks = data)
  }

  age(time : number) {
    return moment(time*1000).fromNow()
  }
};

