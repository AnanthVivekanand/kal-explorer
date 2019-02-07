import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class WalletService {

  constructor(private http: HttpClient) { }

  blocksUrl = `${environment.url_base}/addr`;

  getBalance(address : String) : any {
    return this.http.get(`${this.blocksUrl}/${address}/balance`).toPromise();
  }

  getRichList() : any {
    return this.http.get(`${environment.url_base}/richlist`).toPromise();
  }

  getDistribution() : any {
    return this.http.get(`${environment.url_base}/distribution`).toPromise();
  }
}
