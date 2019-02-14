import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';
import io from 'socket.io-client';

@Injectable({
    providedIn: 'root'
})
export class SocketService {
    socket = io.connect(environment.sio);
    constructor(private http: HttpClient) {
        this.socket.on('connect', () => {
            console.log('Connected');
            this.socket.emit('subscribe', 'inv');
        })
    }
}
