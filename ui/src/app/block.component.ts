import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { BlocksService } from './blocks.service';
import { TransactionBlockComponent } from './components/transaction.component';
import * as moment from 'moment';
import { Observable } from 'rxjs';


@Component({
    selector: 'block',
    templateUrl: './block.component.html',
    styleUrls: ['./block.component.scss']
})
export class BlockComponent implements OnInit {
    title = 'Block';
    block: any;
    sub : any;

    constructor(private router : Router, private route: ActivatedRoute, private blocksService: BlocksService) {
        // blocksService.getBlock(this.route.snapshot.params['blockhash'])
        //     .subscribe((data: any) => this.block = data)
    }

    ngOnInit() {
        this.sub = this.route.params.subscribe(params => {
            const blockhash = params['blockhash'];
            this.blocksService.getBlock(blockhash).toPromise().then(data => { this.block = data });
          });
    }

    timestamp() {
        //Jan 31, 2019 8:20:36 PM
        return moment(this.block.timestamp*1000).format('MMM DD, YYYY H:mm:ss');
    }

    goBlock(blockhash : String) {
        this.router.navigate(['block', blockhash])
    }
};

