<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\UserController;
use App\Http\Controllers\InventoryController;
//Route::get('/', function () {
//    return view('welcome');
//});

Route::get('/', [InventoryController::class, 'index'])->name('inventory.index');
Route::get('/items-data', [InventoryController::class, 'getItemsData'])->name('items.data');
