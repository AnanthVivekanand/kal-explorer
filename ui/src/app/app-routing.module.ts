import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { HomeComponent } from './home.component';
import { BlockComponent } from './block.component';
import { AddressComponent } from './address.component';
import { TransactionComponent } from './transaction.component';

const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'block/:blockhash', component: BlockComponent },
  { path: 'address/:address', component: AddressComponent },
  { path: 'tx/:txid', component: TransactionComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
