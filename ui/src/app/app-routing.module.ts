import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { HomeComponent } from './home.component';
import { BlockComponent } from './block.component';
import { AddressComponent } from './address.component';
import { TransactionComponent } from './transaction.component';
import { RichListComponent } from './richlist.component';
import { WalletComponent } from './wallet/wallet.component';
import { WalletGroupComponent } from './wallet_group.component';

const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'block/:blockhash', component: BlockComponent },
  { path: 'address/:address', component: AddressComponent },
  { path: 'tx/:txid', component: TransactionComponent },
  { path: 'richlist', component: RichListComponent },
  { path: 'wallet', component: WalletComponent },
  { path: 'wallet_group/:walletId', component: WalletGroupComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
