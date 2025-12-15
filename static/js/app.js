// Global state
let tasks = [];
let spaces = [];
let calendar;
let taskModal;
let spaceModal;
let calendarModal;
let sortable;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modals
    taskModal = new bootstrap.Modal(document.getElementById('taskModal'));
    spaceModal = new bootstrap.Modal(document.getElementById('spaceModal'));
    calendarModal = new bootstrap.Modal(document.getElementById('calendarModal'));

    // Initialize calendar
    initCalendar();

    // Initialize sortable task list
    initSortable();

    // Load initial data
    loadTasks();
    loadSpaces();

    // Event listeners
    document.getElementById('parseTaskBtn').addEventListener('click', parseTask);
    document.getElementById('scheduleBtn').addEventListener('click', autoSchedule);
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('addSpaceBtn').addEventListener('click', showSpaceModal);
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
        events: loadCalendarEvents,
        viewDidMount: setupDayHeaderListeners,
        datesSet: setupDayHeaderListeners
    });
    calendar.render();
}

// Setup listeners for day headers to enable Ctrl+Click to freeze days
function setupDayHeaderListeners() {
    // Small delay to ensure DOM is ready
    setTimeout(() => {
        const dayHeaders = document.querySelectorAll('.fc-col-header-cell[data-date]');
        dayHeaders.forEach(header => {
            // Remove existing listener to avoid duplicates
            const newHeader = header.cloneNode(true);
            header.parentNode.replaceChild(newHeader, header);

            // Add click listener
            newHeader.addEventListener('click', function(e) {
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    const dateStr = this.getAttribute('data-date');
                    if (dateStr) {
                        freezeDay(dateStr);
                    }
                }
            });

            // Add visual hint
            newHeader.style.cursor = 'pointer';
            newHeader.title = 'Ctrl+Click to freeze/unfreeze all tasks on this day';
        });
    }, 100);
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
            <div class="task-item ${task.completed ? 'completed' : ''} ${task.frozen ? 'frozen' : ''}" data-task-id="${task.id}">
                <div class="task-priority ${priorityClass}">${task.priority}</div>
                <div class="task-title">${task.frozen ? '❄️ ' : ''}${escapeHtml(task.title)}</div>
                <div class="task-meta">
                    ${task.space ? `<span class="task-space"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(task.space)}</span>` : ''}
                    ${task.estimated_duration ? `<span class="task-meta-item"><i class="fas fa-clock"></i> ${task.estimated_duration}min</span>` : ''}
                    ${deadlineStr ? `<span class="task-meta-item task-deadline ${isSoon ? 'soon' : ''}"><i class="fas fa-calendar-times"></i> ${deadlineStr}</span>` : ''}
                    ${task.scheduled_start ? `<span class="task-meta-item"><i class="fas fa-calendar-check"></i> Scheduled</span>` : ''}
                    ${task.frozen ? `<span class="task-meta-item frozen-indicator"><i class="fas fa-snowflake"></i> Frozen</span>` : ''}
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
            title: task.frozen ? `❄️ ${task.title}` : task.title,
            start: task.scheduled_start,
            end: task.scheduled_end,
            className: task.frozen ? 'task-event frozen-task' : 'task-event',
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
        // Check if Ctrl key is pressed
        if (info.jsEvent.ctrlKey || info.jsEvent.metaKey) {
            // Prevent default action and toggle freeze
            info.jsEvent.preventDefault();
            toggleTaskFreeze(event.extendedProps.taskId);
        } else {
            editTask(event.extendedProps.taskId);
        }
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
    document.getElementById('editSpace').value = task.space || '';
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
        space: document.getElementById('editSpace').value,
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

// Toggle task freeze status
async function toggleTaskFreeze(taskId) {
    const response = await fetch(`/api/tasks/${taskId}/toggle-freeze`, {
        method: 'POST'
    });

    if (response.ok) {
        const result = await response.json();
        await loadTasks();
        calendar.refetchEvents();
        showAlert(
            result.frozen ? '❄️ Task frozen - will not be rescheduled' : '✓ Task unfrozen',
            result.frozen ? 'info' : 'success'
        );
    } else {
        showAlert('Error toggling freeze status', 'danger');
    }
}

// Freeze all tasks on a specific day
async function freezeDay(dateStr) {
    const response = await fetch('/api/tasks/freeze-day', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ date: dateStr })
    });

    if (response.ok) {
        const result = await response.json();
        if (result.count > 0) {
            await loadTasks();
            calendar.refetchEvents();
            showAlert(
                result.frozen
                    ? `❄️ Frozen ${result.count} task(s) on this day`
                    : `✓ Unfrozen ${result.count} task(s) on this day`,
                result.frozen ? 'info' : 'success'
            );
        } else {
            showAlert('No tasks found on this day', 'warning');
        }
    } else {
        showAlert('Error freezing day', 'danger');
    }
}

// Load spaces
async function loadSpaces() {
    const response = await fetch('/api/spaces');
    spaces = await response.json();
    updateSpaceSelects();
}

// Update space selects
function updateSpaceSelects() {
    const select = document.getElementById('editSpace');
    select.innerHTML = '<option value="">None</option>' +
        spaces.map(space => `<option value="${escapeHtml(space.name)}">${escapeHtml(space.name)}</option>`).join('');
}

// Show space modal
async function showSpaceModal() {
    await loadSpaces();
    renderSpaces();
    spaceModal.show();
}

// Render spaces
function renderSpaces() {
    const list = document.getElementById('spaceList');
    list.innerHTML = spaces.map(space => `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-0">${escapeHtml(space.name)}</h6>
                    <div>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editSpace(${space.id})">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteSpace(${space.id})">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                ${space.description ? `<p class="text-muted small mb-2">${escapeHtml(space.description)}</p>` : ''}
                <div class="text-muted small">
                    ${space.time_constraints.length > 0 ?
                        space.time_constraints.map(c =>
                            `${getDayName(c.day)}: ${c.start} - ${c.end}`
                        ).join('<br>') :
                        'No time constraints'
                    }
                </div>
            </div>
        </div>
    `).join('');
}

// Create new space
async function createSpace() {
    const name = document.getElementById('newSpaceName').value.trim();
    const description = document.getElementById('newSpaceDescription').value.trim();

    if (!name) {
        showAlert('Please enter a space name', 'warning');
        return;
    }

    // Collect time constraints
    const constraints = [];
    const constraintInputs = document.querySelectorAll('.time-constraint-item');
    constraintInputs.forEach(item => {
        const day = parseInt(item.querySelector('.constraint-day').value);
        const start = item.querySelector('.constraint-start').value;
        const end = item.querySelector('.constraint-end').value;

        if (start && end) {
            constraints.push({ day, start, end });
        }
    });

    await fetch('/api/spaces', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name,
            description,
            time_constraints: constraints
        })
    });

    // Reset form
    document.getElementById('newSpaceName').value = '';
    document.getElementById('newSpaceDescription').value = '';
    document.getElementById('timeConstraints').innerHTML = '';
    document.getElementById('addSpaceForm').style.display = 'none';

    await loadSpaces();
    renderSpaces();
    showAlert('Space created successfully!', 'success');
}

// Edit space
async function editSpace(spaceId) {
    const space = spaces.find(s => s.id === spaceId);
    if (!space) return;

    // Show edit form
    const list = document.getElementById('spaceList');
    list.innerHTML = `
        <div class="card mb-3">
            <div class="card-body">
                <h6 class="mb-3">Edit Space</h6>
                <div class="mb-3">
                    <label class="form-label">Name</label>
                    <input type="text" class="form-control" id="editSpaceName" value="${escapeHtml(space.name)}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Description</label>
                    <textarea class="form-control" id="editSpaceDescription" rows="2">${escapeHtml(space.description || '')}</textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">Time Constraints</label>
                    <div id="editTimeConstraints">
                        ${space.time_constraints.map((c, idx) => `
                            <div class="time-constraint-item d-flex gap-2 mb-2">
                                <select class="form-select constraint-day" style="width: auto;">
                                    ${['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day, i) =>
                                        `<option value="${i}" ${i === c.day ? 'selected' : ''}>${day}</option>`
                                    ).join('')}
                                </select>
                                <input type="time" class="form-control constraint-start" value="${c.start}" style="width: auto;">
                                <input type="time" class="form-control constraint-end" value="${c.end}" style="width: auto;">
                                <button class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn btn-sm btn-outline-secondary mt-2" onclick="addConstraintToEdit()">
                        <i class="fas fa-plus"></i> Add Time Constraint
                    </button>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-primary" onclick="saveSpaceEdit(${spaceId})">Save</button>
                    <button class="btn btn-secondary" onclick="renderSpaces()">Cancel</button>
                </div>
            </div>
        </div>
    ` + spaces.filter(s => s.id !== spaceId).map(s => `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-0">${escapeHtml(s.name)}</h6>
                    <div>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editSpace(${s.id})">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteSpace(${s.id})">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                ${s.description ? `<p class="text-muted small mb-2">${escapeHtml(s.description)}</p>` : ''}
                <div class="text-muted small">
                    ${s.time_constraints.length > 0 ?
                        s.time_constraints.map(c =>
                            `${getDayName(c.day)}: ${c.start} - ${c.end}`
                        ).join('<br>') :
                        'No time constraints'
                    }
                </div>
            </div>
        </div>
    `).join('');
}

// Save space edit
async function saveSpaceEdit(spaceId) {
    const name = document.getElementById('editSpaceName').value.trim();
    const description = document.getElementById('editSpaceDescription').value.trim();

    if (!name) {
        showAlert('Please enter a space name', 'warning');
        return;
    }

    // Collect time constraints
    const constraints = [];
    const constraintInputs = document.querySelectorAll('#editTimeConstraints .time-constraint-item');
    constraintInputs.forEach(item => {
        const day = parseInt(item.querySelector('.constraint-day').value);
        const start = item.querySelector('.constraint-start').value;
        const end = item.querySelector('.constraint-end').value;

        if (start && end) {
            constraints.push({ day, start, end });
        }
    });

    await fetch(`/api/spaces/${spaceId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name,
            description,
            time_constraints: constraints
        })
    });

    await loadSpaces();
    renderSpaces();
    showAlert('Space updated successfully!', 'success');
}

// Delete space
async function deleteSpace(spaceId) {
    if (!confirm('Are you sure you want to delete this space?')) return;

    await fetch(`/api/spaces/${spaceId}`, {
        method: 'DELETE'
    });

    await loadSpaces();
    renderSpaces();
    showAlert('Space deleted successfully!', 'success');
}

// Show add space form
function showAddSpaceForm() {
    document.getElementById('addSpaceForm').style.display = 'block';
}

// Add time constraint
function addTimeConstraint() {
    const container = document.getElementById('timeConstraints');
    const div = document.createElement('div');
    div.className = 'time-constraint-item d-flex gap-2 mb-2';
    div.innerHTML = `
        <select class="form-select constraint-day" style="width: auto;">
            <option value="0">Monday</option>
            <option value="1">Tuesday</option>
            <option value="2">Wednesday</option>
            <option value="3">Thursday</option>
            <option value="4">Friday</option>
            <option value="5">Saturday</option>
            <option value="6">Sunday</option>
        </select>
        <input type="time" class="form-control constraint-start" style="width: auto;">
        <input type="time" class="form-control constraint-end" style="width: auto;">
        <button class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(div);
}

// Add constraint to edit form
function addConstraintToEdit() {
    const container = document.getElementById('editTimeConstraints');
    const div = document.createElement('div');
    div.className = 'time-constraint-item d-flex gap-2 mb-2';
    div.innerHTML = `
        <select class="form-select constraint-day" style="width: auto;">
            <option value="0">Monday</option>
            <option value="1">Tuesday</option>
            <option value="2">Wednesday</option>
            <option value="3">Thursday</option>
            <option value="4">Friday</option>
            <option value="5">Saturday</option>
            <option value="6">Sunday</option>
        </select>
        <input type="time" class="form-control constraint-start" style="width: auto;">
        <input type="time" class="form-control constraint-end" style="width: auto;">
        <button class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(div);
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
