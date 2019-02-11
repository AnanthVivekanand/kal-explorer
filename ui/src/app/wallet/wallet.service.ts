import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class WalletService {

  constructor(private http: HttpClient) { }

  blocksUrl = `/api/addr`;

  getBalance(address : String) : any {
    return this.http.get(`${this.blocksUrl}/${address}/balance`).toPromise();
  }

  getUtxos(address : String) : any {
    return this.http.get(`${this.blocksUrl}/${address}/utxo`).toPromise();
  }
}
