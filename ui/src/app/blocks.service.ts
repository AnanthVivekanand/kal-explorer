import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';


@Injectable({
  providedIn: 'root'
})
export class BlocksService {

  constructor(private http: HttpClient) {

  }

  blocksUrl = 'http://localhost:5000/blocks';

  getBlocks() {
    return this.http.get(this.blocksUrl);
  }
}
