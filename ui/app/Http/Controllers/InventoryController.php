<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Carbon\Carbon;

class InventoryController extends Controller
{
    public function index()
    {
        $tableName = 'inventory'; // Points to our Wire Harness DB

        // --- 1. Total & Current Month Revenue ---
        $totalRevenue = DB::table($tableName)
            ->sum(DB::raw('Units_Sold * Price * (1 - Discount/100)'));
            
        $totalStock = DB::table($tableName)->sum('Inventory_Level');

        // Find the latest date in the DB to act as our "Current Month"
        $latestDate = DB::table($tableName)->max('Date');
        $currentMonthRevenue = 0;
        
        if ($latestDate) {
            $latestMonth = Carbon::parse($latestDate)->month;
            $latestYear = Carbon::parse($latestDate)->year;
            
            $currentMonthRevenue = DB::table($tableName)
                ->whereMonth('Date', $latestMonth)
                ->whereYear('Date', $latestYear)
                ->sum(DB::raw('Units_Sold * Price * (1 - Discount/100)'));
        }

        // --- 2. Top Performing Products (Fixed: Get top 10, not just 1) ---
        $topProducts = DB::table($tableName)
            ->select('Product_ID', DB::raw('SUM(Units_Sold) as Units_Sold'))
            ->groupBy('Product_ID')
            ->orderBy('Units_Sold', 'desc')
            ->limit(10)
            ->get();

        // --- 3. Category of Sales ---
        $categorySales = DB::table($tableName)
            ->select('Category', 
                DB::raw('SUM(Units_Sold) as total_units'), 
                DB::raw('SUM(Units_Sold * Price * (1 - Discount/100)) as category_revenue')
            )
            ->groupBy('Category')
            ->orderBy('category_revenue', 'desc')
            ->get();

        // --- 4. Sales Trend ---
        // Fixed: Added ->values() so JS sees this as a clean array, not an object
        $salesTrend = DB::table($tableName)
            ->select('Date', DB::raw('SUM(Units_Sold * Price * (1 - Discount/100)) as daily_revenue'))
            ->groupBy('Date')
            ->orderBy('Date', 'desc')
            ->limit(7)
            ->get()
            ->reverse()
            ->values(); 

        // --- 5. Critical Stock Items ---
        $criticalStock = DB::table($tableName)
            ->whereRaw('Inventory_Level < (Units_Sold * 20)')
            ->orderBy('Inventory_Level', 'asc')
            ->limit(8)
            ->get();

        // --- 6. Main Inventory Table ---
        $inventoryRecords = DB::table($tableName)
            ->orderBy('Date', 'desc')
            ->limit(200)
            ->get();

        return view('main', compact(
            'totalRevenue',
            'totalStock',
            'currentMonthRevenue',
            'topProducts',
            'categorySales',
            'salesTrend',
            'criticalStock',
            'inventoryRecords'
        ));
    }
}