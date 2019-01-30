import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';


@Injectable({
  providedIn: 'root'
})
export class StatusService {

  constructor(private http: HttpClient) {

  }

  statusUrl = 'http://localhost:5000/status?q=getInfo';

  getStatus() {
    return this.http.get(this.statusUrl);
  }
}
