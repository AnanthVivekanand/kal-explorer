import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AddressService {

  constructor(private http: HttpClient) { }

  blocksUrl = `${environment.url_base}/address`;

  getBalance(address : String) {
    return this.http.get(`${this.blocksUrl}/${address}`).toPromise();
  }
}
