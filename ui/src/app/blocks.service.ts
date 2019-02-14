import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from '../environments/environment';
import { SocketService } from './socket.service';

@Injectable({
  providedIn: 'root'
})
export class BlocksService {

  blocksObservable : Observable<any>

  constructor(private http: HttpClient, private socketService : SocketService) {
    const blockSource = new BehaviorSubject(null);
    this.blocksObservable = blockSource.asObservable();

    socketService.socket.on('block', function(block) {
      blockSource.next(block);
    });
  }

  blocksUrl = `${environment.url_base}/blocks`;

  getBlocks(limit : Number) {
    return this.http.get(`${this.blocksUrl}?limit=${limit}`);
  }

  getBlock(blockhash : String) {
    return this.http.get(`${environment.url_base}/block/${blockhash}`);
  }
}
