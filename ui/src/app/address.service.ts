import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AddressService {

  constructor(private http: HttpClient) { }

  blocksUrl = `${environment.url_base}/addr`;

  getBalance(address : String) : any {
    return this.http.get(`${this.blocksUrl}/${address}/balance`).toPromise();
  }

  getInfo(address : String) : any {
    return this.http.get(`${this.blocksUrl}/${address}`).toPromise();
  }

  getRichList() : any {
    return this.http.get(`${environment.url_base}/richlist`).toPromise();
  }

  getDistribution() : any {
    return this.http.get(`${environment.url_base}/distribution`).toPromise();
  }

  getWallet(walletId : string) : any{
    return this.http.get(`${environment.url_base}/wallet_groups/${walletId}`).toPromise();
  }
}
