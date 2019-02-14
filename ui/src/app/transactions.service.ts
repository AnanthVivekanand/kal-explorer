import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';
import { SocketService } from './socket.service';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TransactionService {

  txObservable : Observable<any>

  constructor(private http: HttpClient, private socketService : SocketService) {
    const txSource = new BehaviorSubject(null);
    this.txObservable = txSource.asObservable();
    socketService.socket.on('tx', function(tx) {
      txSource.next(tx);
    });
  }

  txUrl = `${environment.url_base}`;

  getTransactions(addr : string, lastTime : Number) : any {
    if(lastTime != null){
      return this.http.get(`${this.txUrl}/txs/${addr}?beforeTime=${lastTime}`).toPromise();  
    }
    return this.http.get(`${this.txUrl}/txs/${addr}`).toPromise();
  }

  getTransaction(txid : string) : Promise<any> {
    return this.http.get(`${this.txUrl}/tx/${txid}`).toPromise();
  }
}
