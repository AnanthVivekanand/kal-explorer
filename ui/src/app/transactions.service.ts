import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class TransactionService {

  constructor(private http: HttpClient) { }

  txUrl = `${environment.url_base}`;

  getTransactions(addr : string, lastTime : Number) : any {
    if(lastTime != null){
      return this.http.get(`${this.txUrl}/txs/${addr}?beforeTime=${lastTime}`).toPromise();  
    }
    return this.http.get(`${this.txUrl}/txs/${addr}`).toPromise();
  }

  getTransaction(txid : string) : any {
    return this.http.get(`${this.txUrl}/tx/${txid}`).toPromise();
  }
}
