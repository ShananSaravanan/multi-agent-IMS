<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>RetailAI - Multi-Agent System</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">

    {{--    Bootstrap CSS and JS--}}
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/apexcharts/3.44.0/apexcharts.min.js"></script>

    <link href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="{{asset('style.css')}}">
</head>
<body>
    <header class="dashboard-header">
        <div class="container">
            <div class="header-content">
                <div class="header-title">
                    <div class="card-icon icon-sales">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <h1>Retail Dashboard</h1>
                </div>

                Admin
            </div>
        </div>
    </header>

    <main class="container my-4">
        <div class="stats-grid">
            <div class="stat-card sales">
                <div class="stat-value">${{ number_format($totalRevenue ?? 0, 0) }}</div>
                <div class="stat-label">Total Revenue This Year</div>
                @php
                    $is_increasing = true;
                    $diff_percentage = 12.5;
                @endphp
                @if($is_increasing)
                    <div class="stat-change positive">
                        <i class="fas fa-arrow-up"></i>
                        {{number_format($diff_percentage, 2)}}% vs last year
                    </div>
                @else
                    <div class="stat-change negative">
                        <i class="fas fa-arrow-down"></i>
                        {{number_format($diff_percentage, 2)}}% vs last year
                    </div>
                @endif
            </div>
            <div class="stat-card revenue">
                <div class="stat-value">${{ number_format($currentMonthRevenue ?? 0, 0) }}</div>
                <div class="stat-label">Current Month Revenue</div>
                @php
                    $is_increasing = true;
                    $diff_percentage = 8.2;
                @endphp
                @if($is_increasing)
                    <div class="stat-change positive">
                        <i class="fas fa-arrow-up"></i>
                        {{number_format($diff_percentage, 1)}}% vs last month
                    </div>
                @else
                    <div class="stat-change negative">
                        <i class="fas fa-arrow-down"></i>
                       {{number_format($diff_percentage, 1)}}% vs last month
                    </div>
                @endif
            </div>
            <div class="stat-card inventory">
                <div class="stat-value">{{ number_format($totalStock ?? 0) }}</div>
                <div class="stat-label">Total Stock Units</div>
            </div>
            <div class="stat-card critical">
                <div class="stat-value">{{ count($criticalStock ?? []) }}</div>
                <div class="stat-label">Critical Stock Items</div>
                <div class="stat-change negative">
                    <i class="fas fa-exclamation-triangle"></i>
                    Needs attention
                </div>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-lg-8">
                <div class="dashboard-card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon icon-trends">
                                <i class="fas fa-chart-area"></i>
                            </div>
                            Sales Trends (Recent Dates)
                        </div>
                    </div>
                    <div class="chart-container" id="salesTrendsChart"></div>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="dashboard-card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon icon-sales">
                                <i class="fas fa-chart-pie"></i>
                            </div>
                            Category Sales
                        </div>
                    </div>
                    <div class="chart-container-small" id="categorySalesChart"></div>
                </div>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-lg-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon icon-products">
                                <i class="fas fa-trophy"></i>
                            </div>
                            Top 10 Products Sold
                        </div>
                    </div>
                    <div class="chart-container" id="topProductsChart"></div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon" style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);">
                                <i class="fas fa-exclamation-triangle"></i>
                            </div>
                            Critical Inventory Items
                        </div>
                    </div>
                    <div class="critical-items-table">
                        <table>
                            <thead>
                            <tr>
                                <th>Store ID</th>
                                <th>Product ID</th>
                                <th>Current Stock</th>
                                <th>Avg. Sales</th>
                                <th>Status</th>
                            </tr>
                            </thead>
                            <tbody>
                            @if(isset($criticalStock) && count($criticalStock) > 0)
                                @foreach($criticalStock as $item)
                                    <tr>
                                        <td>{{ $item->Store_ID ?? 'BM-01' }}</td>
                                        <td>{{ $item->Product_ID }}</td>
                                        <td>{{ number_format($item->Inventory_Level, 0) }}</td>
                                        <td>{{ number_format($item->Units_Sold, 1) }}</td>
                                        <td><span class="status-badge status-critical">Critical</span></td>
                                    </tr>
                                @endforeach
                            @else
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 2rem;">
                                        <i class="fas fa-check-circle" style="color: var(--success); font-size: 2rem; margin-bottom: 1rem;"></i><br>
                                        All inventory levels are healthy!
                                    </td>
                                </tr>
                            @endif
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="row pb-5">
            <div class="col-12">
                <div class="dashboard-card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon" style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);">
                                <i class="fas fa-table"></i>
                            </div>
                                Inventory Items
                        </div>
                    </div>
                    <div class="critical-items-table">
                        <table id="criticalItemsTable" class="table table-bordered display nowrap" style="width:100%">
                            <thead>
                            <tr>
                                <th>Store ID</th>
                                <th>Product ID</th>
                                <th>Category</th>
                                <th>Current Stock</th>
                                <th>Avg. Sales</th>
                            </tr>
                            </thead>
                        </table>
                    </div>
                </div>
            </div>
        </div>

    </main>
    {{--for ai chatbot--}}
    <button id="btn-toggle-chatbot" class="button-confetti">
        <i class="fas fa-robot"></i>
    </button>
    @include('chat')
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        const salesTrendsData = @json($salesTrend ?? []);
        const categorySalesData = @json($categorySales ?? []);
        const topProductsData = @json($topProducts ?? []);

        // Sales Trends Chart
        if(salesTrendsData.length > 0) {
            const salesTrendsOptions = {
                series: [{
                    name: 'Revenue',
                    data: salesTrendsData.map(item => parseInt(item.daily_revenue))
                }],
                chart: {
                    type: 'area',
                    height: 350,
                    background: 'transparent',
                    toolbar: { show: false }
                },
                colors: ['#6366f1'],
                fill: {
                    type: 'gradient',
                    gradient: {
                        shadeIntensity: 1,
                        opacityFrom: 0.7,
                        opacityTo: 0.1,
                        stops: [0, 100]
                    }
                },
                dataLabels: { enabled: false },
                stroke: { curve: 'smooth', width: 3 },
                xaxis: {
                    categories: salesTrendsData.map(item => item.Date),
                    labels: { style: { colors: '#8892a6' } },
                    axisBorder: { show: false },
                    axisTicks: { show: false }
                },
                yaxis: {
                    labels: {
                        style: { colors: '#8892a6' },
                        formatter: (value) => '$' + value.toLocaleString()
                    }
                },
                grid: { borderColor: '#2d3748', strokeDashArray: 3 },
                theme: { mode: 'dark' }
            };

            const salesTrendsChart = new ApexCharts(document.querySelector("#salesTrendsChart"), salesTrendsOptions);
            salesTrendsChart.render();
        }

        // Category Sales Chart
        if(categorySalesData.length > 0) {
            const categorySalesOptions = {
                series: categorySalesData.map(item => parseInt(item.category_revenue)),
                chart: {
                    type: 'donut',
                    height: 400,
                    background: 'transparent'
                },
                labels: categorySalesData.map(item => item.Category),
                colors: ['#6366f1', '#f093fb', '#4facfe', '#f6b362', '#43e97b'],
                legend: {
                    position: 'bottom',
                    labels: { colors: '#8892a6' }
                },
                plotOptions: {
                    pie: {
                        donut: {
                            size: '68%',
                            labels: {
                                show: true,
                                name: {
                                    show: true,
                                    color: '#fff'
                                },
                                value: {
                                    show: true,
                                    color: '#fff',
                                    formatter: (val) => '$' + parseFloat(val).toLocaleString()
                                },
                                total: {
                                    show: true,
                                    color: '#ffffff',
                                    formatter: () =>
                                        '$' +
                                        categorySalesData
                                            .reduce((sum, item) => sum + parseInt(item.category_revenue), 0)
                                            .toLocaleString()
                                }
                            }
                        }
                    }
                },
                tooltip: {
                    y: {
                        formatter: (val) => '$' + parseFloat(val).toLocaleString()
                    }
                },
                theme: { mode: 'dark' }
            };

            const categorySalesChart = new ApexCharts(document.querySelector("#categorySalesChart"), categorySalesOptions);
            categorySalesChart.render();
        }

        // Top Products Chart
        if(topProductsData.length > 0) {
            const topProductsOptions = {
                series: [{
                    name: 'Units Sold',
                    data: topProductsData.map(item => parseInt(item.Units_Sold))
                }],
                chart: {
                    type: 'bar',
                    height: 350,
                    background: 'transparent',
                    toolbar: { show: false }
                },
                colors: ['#6366f1'],
                plotOptions: {
                    bar: {
                        borderRadius: 8,
                        horizontal: true,
                        distributed: true
                    }
                },
                dataLabels: { enabled: false },
                xaxis: {
                    categories: topProductsData.map(item => item.Product_ID),
                    labels: { style: { colors: '#8892a6' } }
                },
                yaxis: {
                    labels: { style: { colors: '#8892a6' } }
                },
                grid: { borderColor: '#2d3748', strokeDashArray: 3 },
                theme: { mode: 'dark' }
            };

            const topProductsChart = new ApexCharts(document.querySelector("#topProductsChart"), topProductsOptions);
            topProductsChart.render();
        }
    </script>
<script>
    let currentEventSource = null;
    let isStreaming = false;
    let currentAiMessage = null;


    // Auto-resize textarea
    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    // Handle Enter key
    function handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    }

    // Send suggestion
    function sendSuggestion(text) {
        document.getElementById('messageInput').value = text;
        sendMessage();
    }


    async function sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        if (!message || isStreaming) return;

        // Reset UI
        input.value = '';
        hideWelcomeMessage();
        addMessage(message, 'user');
        showTypingIndicator();
        autoResize(document.querySelector("#messageInput"));
        document.getElementById('sendButton').disabled = true;
        document.getElementById('cancelButton').disabled = false;
        isStreaming = true;

        // Create AI message container
        currentAiMessage = document.createElement('div');
        currentAiMessage.className = 'message ai';
        const content = `
         <div class="message-content">
                <span></span>
                <div class="message-time"></div>
            </div>
        `

        currentAiMessage.innerHTML = content;
        document.getElementById('messagesArea').appendChild(currentAiMessage);

        try {
            const sessionId = getCookie('session_id') || generateUUID();
            document.cookie = `session_id=${sessionId}; path=/`;

            currentEventSource = new EventSource(
                `http://localhost:8181/retail-ai/stream?message=${encodeURIComponent(message)}`,
                { withCredentials: true }
            );

            const contentSpan = currentAiMessage.querySelector('span');

            currentEventSource.onmessage = (event) => {
                if (event.data === "[DONE]" || event.data === "[CANCELLED]") {
                    if (event.data === "[CANCELLED]") {
                        contentSpan.innerHTML += '<em id="message-cancel">Response was cancelled</em>';
                    }
                    updateTimestamp();
                    finishStream();
                    return;
                }
                contentSpan.innerHTML += marked.parse(event.data);
            };

            currentEventSource.onerror = () => {
                contentSpan.innerHTML += '<em>Connection error occurred</em>';
                updateTimestamp();
                finishStream();
            };

        } catch (error) {
            console.error('Error:', error);
            if (currentAiMessage) {
                currentAiMessage.querySelector('span').innerHTML = '<em>Failed to start stream</em>';
                updateTimestamp();
            }
            finishStream();
        }
    }

    function updateTimestamp() {
        if (currentAiMessage) {
            const timeDiv = currentAiMessage.querySelector('.message-time');
            timeDiv.textContent = new Date().toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    function finishStream() {
        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }

        // Remove cancel button
        if (currentAiMessage) {
            const cancelBtn = currentAiMessage.querySelector('.cancel-button');
            if (cancelBtn) cancelBtn.remove();
        }

        hideTypingIndicator();
        document.getElementById('sendButton').disabled = false;
        document.getElementById('cancelButton').disabled = true;
        isStreaming = false;
        currentAiMessage = null;
    }

    async function cancelStream() {
        if (!isStreaming) return;

        try {
            await fetch('http://localhost:8181/retail-ai/cancel', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Cancellation failed:', error);
        }
    }

    // Helper function to get cookies
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    // Helper function to generate UUID
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    // Add message to chat
    function addMessage(text, sender, agents = null) {
        const messagesArea = document.getElementById('messagesArea');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const now = new Date();
        const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        let agentStatus = '';
        if (agents && sender === 'ai') {
            agentStatus = `
                    <div class="agent-status">
                        ${agents.map(agent => `
                            <div class="agent-badge ${agent.active ? 'active' : ''}">
                                <i class="fas fa-circle" style="font-size: 0.5rem;"></i>
                                ${agent.name}
                            </div>
                        `).join('')}
                    </div>
                `;
        }

        messageDiv.innerHTML = `
                <div class="message-content">
                    ${text}
                    <div class="message-time">${time}</div>
                    ${agentStatus}
                </div>
            `;

        messagesArea.appendChild(messageDiv);
        // Use setTimeout to ensure the message is rendered before scrolling
        setTimeout(() => {
            const messagesContainer = document.getElementById('messagesContainer');
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 10);
    }

    // Show/hide typing indicator
    function showTypingIndicator() {
        // Remove existing typing indicator if it exists
        const existingIndicator = document.getElementById('typingIndicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        // Create and append typing indicator at the end of messages
        const messagesContainer = document.getElementById('messagesContainer');
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.id = 'typingIndicator';
        typingIndicator.style.display = 'flex';
        typingIndicator.innerHTML = `
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span>Agents are working...</span>
            `;

        messagesContainer.appendChild(typingIndicator);

        // Scroll to bottom
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 10);
    }

    function hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // Hide welcome message
    function hideWelcomeMessage() {
        const welcomeMessage = document.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
    }

    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        
        // FIXED DATATABLE: Replaced broken AJAX with local JSON data!
        const inventoryData = @json($inventoryRecords ?? []);
        $('#criticalItemsTable').DataTable({
            data: inventoryData,
            columns: [
                { data: 'Store_ID', defaultContent: 'BM-01' },
                { data: 'Product_ID' },
                { data: 'Category' },
                { data: 'Inventory_Level', render: $.fn.dataTable.render.number(',', '.', 0) },
                { data: 'Units_Sold', render: $.fn.dataTable.render.number(',', '.', 1) }
            ],
            order: [[0, 'asc'], [1, 'asc']],
            responsive: true
        });

        document.getElementById('messageInput').focus();

        // EVENT HANDLERS
        document.querySelector('#cancelButton').onclick = () => {
            cancelStream();
            setTimeout(cancelStream, 100); 
        };

        // Toggle the chatbot
        document.querySelector("#btn-toggle-chatbot").onclick = () => {
            document.querySelector('.chat-container').classList.add('open')
        }
        document.querySelector("#btn-close-chatbot").onclick = () => {
            document.querySelector('.chat-container').classList.remove('open')
        }
    });
</script>
</body>
</html>