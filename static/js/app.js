// Global state
let tasks = [];
let locations = [];
let calendar;
let taskModal;
let locationModal;
let calendarModal;
let sortable;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modals
    taskModal = new bootstrap.Modal(document.getElementById('taskModal'));
    locationModal = new bootstrap.Modal(document.getElementById('locationModal'));
    calendarModal = new bootstrap.Modal(document.getElementById('calendarModal'));

    // Initialize calendar
    initCalendar();

    // Initialize sortable task list
    initSortable();

    // Load initial data
    loadTasks();
    loadLocations();

    // Event listeners
    document.getElementById('parseTaskBtn').addEventListener('click', parseTask);
    document.getElementById('scheduleBtn').addEventListener('click', autoSchedule);
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('addLocationBtn').addEventListener('click', showLocationModal);
    document.getElementById('addCalendarBtn').addEventListener('click', showCalendarModal);
    document.getElementById('saveTaskBtn').addEventListener('click', saveTask);
    document.getElementById('deleteTaskBtn').addEventListener('click', deleteTask);
    document.getElementById('saveCalendarBtn').addEventListener('click', saveCalendar);

    // Allow Enter key in task input to submit
    document.getElementById('taskInput').addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            parseTask();
        }
    });
});

// Initialize FullCalendar
function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridWeek,timeGridDay,dayGridMonth'
        },
        slotMinTime: '06:00:00',
        slotMaxTime: '23:00:00',
        height: 'auto',
        editable: true,
        droppable: true,
        eventClick: handleEventClick,
        eventDrop: handleEventDrop,
        eventResize: handleEventResize,
        events: loadCalendarEvents
    });
    calendar.render();
}

// Initialize sortable for task list
function initSortable() {
    const taskList = document.getElementById('taskList');
    sortable = new Sortable(taskList, {
        animation: 150,
        ghostClass: 'dragging',
        onEnd: handleTaskReorder
    });
}

// Load tasks
async function loadTasks() {
    const response = await fetch('/api/tasks');
    tasks = await response.json();
    renderTasks();
}

// Render tasks
function renderTasks() {
    const taskList = document.getElementById('taskList');

    if (tasks.length === 0) {
        taskList.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-clipboard-list fa-3x mb-3"></i>
                <p>No tasks yet. Create your first task above!</p>
            </div>
        `;
        return;
    }

    taskList.innerHTML = tasks.map(task => {
        const priorityClass = task.priority >= 7 ? 'priority-high' :
                             task.priority >= 4 ? 'priority-medium' : 'priority-low';

        const deadline = task.deadline ? new Date(task.deadline) : null;
        const deadlineStr = deadline ? formatDeadline(deadline) : '';
        const isSoon = deadline && (deadline - new Date()) < 24 * 60 * 60 * 1000;

        return `
            <div class="task-item ${task.completed ? 'completed' : ''}" data-task-id="${task.id}">
                <div class="task-priority ${priorityClass}">${task.priority}</div>
                <div class="task-title">${escapeHtml(task.title)}</div>
                <div class="task-meta">
                    ${task.location ? `<span class="task-location"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(task.location)}</span>` : ''}
                    ${task.estimated_duration ? `<span class="task-meta-item"><i class="fas fa-clock"></i> ${task.estimated_duration}min</span>` : ''}
                    ${deadlineStr ? `<span class="task-meta-item task-deadline ${isSoon ? 'soon' : ''}"><i class="fas fa-calendar-times"></i> ${deadlineStr}</span>` : ''}
                    ${task.scheduled_start ? `<span class="task-meta-item"><i class="fas fa-calendar-check"></i> Scheduled</span>` : ''}
                </div>
            </div>
        `;
    }).join('');

    // Add click handlers to task items
    document.querySelectorAll('.task-item').forEach(item => {
        item.addEventListener('click', () => {
            const taskId = parseInt(item.dataset.taskId);
            editTask(taskId);
        });
    });
}

// Parse task with AI
async function parseTask() {
    const input = document.getElementById('taskInput');
    const text = input.value.trim();

    if (!text) {
        showAlert('Please enter a task description', 'warning');
        return;
    }

    const btn = document.getElementById('parseTaskBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading"></span> Creating...';
    btn.disabled = true;

    const response = await fetch('/api/tasks/parse', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    });

    if (response.ok) {
        input.value = '';
        await loadTasks();
        calendar.refetchEvents();
        showAlert('Task created successfully!', 'success');
    } else {
        const error = await response.json();
        showAlert(error.error || 'Error creating task', 'danger');
    }

    btn.innerHTML = originalText;
    btn.disabled = false;
}

// Auto-schedule tasks
async function autoSchedule() {
    const btn = document.getElementById('scheduleBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading"></span> Scheduling...';
    btn.disabled = true;

    const response = await fetch('/api/schedule', {
        method: 'POST'
    });

    if (response.ok) {
        const result = await response.json();
        await loadTasks();
        calendar.refetchEvents();
        showAlert(`Successfully scheduled ${result.scheduled_tasks} tasks!`, 'success');
    } else {
        const error = await response.json();
        showAlert(error.error || 'Error scheduling tasks', 'danger');
    }

    btn.innerHTML = originalText;
    btn.disabled = false;
}

// Load calendar events
async function loadCalendarEvents(fetchInfo, successCallback, failureCallback) {
    // Load tasks
    const taskResponse = await fetch('/api/tasks');
    const tasks = await taskResponse.json();

    // Load external events
    const externalResponse = await fetch('/api/external-events');
    const externalEvents = await externalResponse.json();

    // Format task events
    const taskEvents = tasks
        .filter(task => task.scheduled_start && task.scheduled_end && !task.completed)
        .map(task => ({
            id: `task-${task.id}`,
            title: task.title,
            start: task.scheduled_start,
            end: task.scheduled_end,
            className: 'task-event',
            extendedProps: {
                type: 'task',
                taskId: task.id,
                task: task
            }
        }));

    // Format external events
    const formattedExternalEvents = externalEvents.map((event, index) => ({
        id: `external-${index}`,
        title: event.title,
        start: event.start,
        end: event.end,
        className: 'external-event',
        editable: false,
        extendedProps: {
            type: 'external',
            description: event.description
        }
    }));

    successCallback([...taskEvents, ...formattedExternalEvents]);
}

// Handle event click
function handleEventClick(info) {
    const event = info.event;

    if (event.extendedProps.type === 'task') {
        editTask(event.extendedProps.taskId);
    }
}

// Handle event drop (drag)
async function handleEventDrop(info) {
    const event = info.event;

    if (event.extendedProps.type === 'task') {
        const taskId = event.extendedProps.taskId;
        const newStart = event.start.toISOString();
        const newEnd = event.end.toISOString();

        await updateTaskSchedule(taskId, newStart, newEnd);
        await loadTasks();
    }
}

// Handle event resize
async function handleEventResize(info) {
    const event = info.event;

    if (event.extendedProps.type === 'task') {
        const taskId = event.extendedProps.taskId;
        const newStart = event.start.toISOString();
        const newEnd = event.end.toISOString();

        // Calculate new duration
        const duration = Math.round((event.end - event.start) / 60000); // in minutes

        await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scheduled_start: newStart,
                scheduled_end: newEnd,
                estimated_duration: duration
            })
        });
        await loadTasks();
    }
}

// Update task schedule
async function updateTaskSchedule(taskId, start, end) {
    await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            scheduled_start: start,
            scheduled_end: end
        })
    });
}

// Handle task reorder
async function handleTaskReorder(evt) {
    const taskIds = Array.from(document.querySelectorAll('.task-item')).map(item =>
        parseInt(item.dataset.taskId)
    );

    await fetch('/api/tasks/reorder', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ task_ids: taskIds })
    });
    await loadTasks();
}

// Edit task
function editTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    document.getElementById('editTaskId').value = task.id;
    document.getElementById('editTitle').value = task.title;
    document.getElementById('editDescription').value = task.description || '';
    document.getElementById('editLocation').value = task.location || '';
    document.getElementById('editPriority').value = task.priority;
    document.getElementById('editDuration').value = task.estimated_duration || 60;
    document.getElementById('editCompleted').checked = task.completed;

    if (task.deadline) {
        const deadline = new Date(task.deadline);
        document.getElementById('editDeadline').value = formatDateTimeLocal(deadline);
    } else {
        document.getElementById('editDeadline').value = '';
    }

    taskModal.show();
}

// Save task
async function saveTask() {
    const taskId = parseInt(document.getElementById('editTaskId').value);
    const data = {
        title: document.getElementById('editTitle').value,
        description: document.getElementById('editDescription').value,
        location: document.getElementById('editLocation').value,
        priority: parseInt(document.getElementById('editPriority').value),
        estimated_duration: parseInt(document.getElementById('editDuration').value),
        completed: document.getElementById('editCompleted').checked,
        deadline: document.getElementById('editDeadline').value ?
                 new Date(document.getElementById('editDeadline').value).toISOString() : null
    };

    await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    taskModal.hide();
    await loadTasks();
    calendar.refetchEvents();
    showAlert('Task updated successfully!', 'success');
}

// Delete task
async function deleteTask() {
    if (!confirm('Are you sure you want to delete this task?')) return;

    const taskId = parseInt(document.getElementById('editTaskId').value);

    await fetch(`/api/tasks/${taskId}`, {
        method: 'DELETE'
    });

    taskModal.hide();
    await loadTasks();
    calendar.refetchEvents();
    showAlert('Task deleted successfully!', 'success');
}

// Load locations
async function loadLocations() {
    const response = await fetch('/api/locations');
    locations = await response.json();
    updateLocationSelects();
}

// Update location selects
function updateLocationSelects() {
    const select = document.getElementById('editLocation');
    select.innerHTML = '<option value="">None</option>' +
        locations.map(loc => `<option value="${escapeHtml(loc.name)}">${escapeHtml(loc.name)}</option>`).join('');
}

// Show location modal
async function showLocationModal() {
    await loadLocations();
    renderLocations();
    locationModal.show();
}

// Render locations
function renderLocations() {
    const list = document.getElementById('locationList');
    list.innerHTML = locations.map(loc => `
        <div class="card mb-3">
            <div class="card-body">
                <h6>${escapeHtml(loc.name)}</h6>
                <div class="text-muted small">
                    ${loc.time_constraints.length > 0 ?
                        loc.time_constraints.map(c =>
                            `${getDayName(c.day)}: ${c.start} - ${c.end}`
                        ).join('<br>') :
                        'No time constraints'
                    }
                </div>
            </div>
        </div>
    `).join('');
}

// Show calendar modal
async function showCalendarModal() {
    await loadCalendarSources();
    calendarModal.show();
}

// Load calendar sources
async function loadCalendarSources() {
    const response = await fetch('/api/calendar-sources');
    const sources = await response.json();

    const list = document.getElementById('existingCalendars');
    if (sources.length > 0) {
        list.innerHTML = '<h6 class="mb-2">Existing Calendars:</h6>' +
            sources.map(source => `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>${escapeHtml(source.name)}</span>
                    <button class="btn btn-sm btn-danger" onclick="deleteCalendarSource(${source.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `).join('');
    } else {
        list.innerHTML = '';
    }
}

// Save calendar source
async function saveCalendar() {
    const name = document.getElementById('calendarName').value;
    const url = document.getElementById('calendarUrl').value;

    if (!name || !url) {
        showAlert('Please enter both name and URL', 'warning');
        return;
    }

    await fetch('/api/calendar-sources', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, ics_url: url })
    });

    document.getElementById('calendarName').value = '';
    document.getElementById('calendarUrl').value = '';
    await loadCalendarSources();
    calendar.refetchEvents();
    showAlert('Calendar added successfully!', 'success');
}

// Delete calendar source
async function deleteCalendarSource(sourceId) {
    if (!confirm('Are you sure you want to remove this calendar?')) return;

    await fetch(`/api/calendar-sources/${sourceId}`, {
        method: 'DELETE'
    });

    await loadCalendarSources();
    calendar.refetchEvents();
    showAlert('Calendar removed successfully!', 'success');
}

// Logout
async function logout() {
    await fetch('/logout', { method: 'POST' });
    window.location.href = '/login';
}

// Utility functions
function showAlert(message, type) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alert);

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        alert.remove();
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDeadline(date) {
    const now = new Date();
    const diff = date - now;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days < 0) return 'Overdue';
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    if (days < 7) return `${days} days`;

    return date.toLocaleDateString();
}

function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function getDayName(dayIndex) {
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    return days[dayIndex];
}
