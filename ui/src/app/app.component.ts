import { Component } from '@angular/core';
import { StatusService } from './status.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'ui';
  status = {};

  constructor(statusService : StatusService){
    statusService.getStatus()
    .subscribe((data: [any]) => this.status = data)
  }

}
