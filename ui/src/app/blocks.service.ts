import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from '../environments/environment';
import io from 'socket.io-client';

@Injectable({
  providedIn: 'root'
})
export class BlocksService {

  blocksObservable : Observable<{}>

  constructor(private http: HttpClient) {
    const socket = io.connect(environment.sio);
    const blockSource = new BehaviorSubject({});
    this.blocksObservable = blockSource.asObservable();

    socket.on('block', function(block) {
      blockSource.next(block);
    });
    socket.on('tx', function(tx) {
      console.log(tx);
    })
    socket.on('connect', () => {
      console.log('Connected');
      socket.emit('subscribe', 'inv');
    })
  }

  blocksUrl = `${environment.url_base}/blocks`;

  getBlocks(limit : Number) {
    return this.http.get(`${this.blocksUrl}?limit=${limit}`);
  }

  getBlock(blockhash : String) {
    return this.http.get(`${environment.url_base}/block/${blockhash}`);
  }
}
