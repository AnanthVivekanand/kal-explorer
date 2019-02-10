import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { HomeComponent } from './home.component';
import { BlockComponent } from './block.component';
import { AddressComponent } from './address.component';
import { TransactionComponent } from './transaction.component';
import { TransactionBlockComponent } from './components/transaction.component';
import { RichListComponent } from './richlist.component';
import { WalletComponent } from './wallet/wallet.component';

import { MDBBootstrapModule } from 'angular-bootstrap-md';
import { HttpClientModule } from '@angular/common/http';

import { NgxQRCodeModule } from 'ngx-qrcode2';
import { InfiniteScrollModule } from 'ngx-infinite-scroll';
import { FormsModule } from '@angular/forms';
import { Title }  from '@angular/platform-browser';



@NgModule({
  declarations: [
    AppComponent,
    HomeComponent,
    BlockComponent,
    TransactionComponent,
    AddressComponent,
    RichListComponent,
    TransactionBlockComponent,
    WalletComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    MDBBootstrapModule.forRoot(),
    HttpClientModule,
    NgxQRCodeModule,
    FormsModule,
    InfiniteScrollModule
  ],
  providers: [Title],
  bootstrap: [AppComponent]
})
export class AppModule { }
