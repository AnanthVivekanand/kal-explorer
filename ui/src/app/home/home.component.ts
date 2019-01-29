import { Component } from '@angular/core';
import { BlocksService } from '../blocks.service';

@Component({
  selector: 'home',
  templateUrl: './home.component.html',
//   styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  title = 'ui';
  blocks : any [];

  constructor(blocksService : BlocksService) {
    blocksService.getBlocks()
    .subscribe((data: [Block]) => this.blocks = data)
  }
};

export interface Block {
    heroesUrl: string;
    textfile: string;
}