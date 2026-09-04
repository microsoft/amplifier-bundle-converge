import { renderTop } from './render/top.js';
import { renderOperation } from './render/operation.js';
import { renderConsole, watchLane } from './render/console.js';
import { wireEditing, openFeedback, openSteer, fillLanes } from './actions.js';
export function renderAll() { renderTop(); renderOperation(data.operation); renderConsole(); }
