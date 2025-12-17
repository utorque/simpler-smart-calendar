# TODOS

## NEXT TODO
- [ ] global user config (breaks, breaks after tasks, work times for everything). update the db accordingly and create a migrate.py using sqlite directly so it can work for prod database.
- [ ] add green hosting label -> <img src="https://app.greenweb.org/api/v3/greencheckimage/simpler.utorque.ch?nocache=true" alt="This website runs on green hosting - verified by thegreenwebfoundation.org" width="200px" height="95px">
- [ ] clic/dragclic calendar to create a task (paste text as the rest)
- [ ] shift+drag on the calendar to reserve timespan for a space
- [ ] advanced task creator that opens a modal to manually create one. Should be oneclic in a square next to the input task. If there is text in the input task, that text is added in the description of the advanced task creator, fill in all blanks and either manually create task directly (enter) or AI-create (ctrl-enter) : send the task to the AI and it recreates it, maybe it will just summarize it or create subtasks or whatever


## GOOD FEATURES
- [ ] fully redo the UI to be nicer, more responsive, softer to the eye while prioritizing UX- Potentially change the stack ?

- [ ] direct filter on task list to see only X or Y places
- [ ] button to reschedule only for current filter
- [ ] add audio task using infomaniak whisper api
- [ ] add telegram bot with n8n
- [ ] Add "Overall view" with a global dashboard and informations with task list, groups etc instead of calendar. UX research opportunity for good things ? Research tailored for ADHD ?


## PLANNED
- [ ] investigate not all tasks planned when many tasked ?
- [ ] add list view to calendar

## MAYBE LATER
- [ ] task button add context and re-plan
- [ ] button to automatically do docker-compose pull and docker-compose up -d from the web app (supersecure lol)
- [ ] add a done button or sth
- [ ] get all tasks for context or something ?  
- [ ] add learn user habits   
- [ ] optimize system prompt

## MEH
- [ ] Potentially going all in in project management ?

## DONE
- [x] LOOKS FIXED ? add the current date and time to the planner so it does not plan things for too early
- [x] redo ai api to be generic / use mistral or cheaper & less energy intensive models ; infomaniak api looks cheap (mistral 24b instruct) ; I suppose use openai python interface with api url and apikey as env variables.
- [x] add space id and not name directly to change name lol
- [x] Make AI return list of tasks instead of just one necessarily
- [x] Drag task edge on calendar to change time
- [x] way to see tasks finished
- [x] ctrl click to mark task done
- [x] lock/freeze tasks on modification in the calendar (ctrl click or sth)
