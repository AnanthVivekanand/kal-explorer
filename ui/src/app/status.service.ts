import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({
    providedIn: 'root'
})
export class StatusService {
    statusUrl = `${environment.url_base}/status?q=getInfo`;

    constructor(private http: HttpClient) {
        console.log(this.statusUrl);
    }

    private statusSource = new BehaviorSubject({});
    currentStatus = this.statusSource.asObservable();

    async updateStatus() {
        const status = await this.http.get(this.statusUrl).toPromise();
        this.statusSource.next(status);
    }
}
