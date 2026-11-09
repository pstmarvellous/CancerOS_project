import { afterEach, expect, it, vi } from 'vitest';
import { researchJson } from './research-client';
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();});
it('bounds a stalled request and retains caller cancellation',async()=>{
  const timeout=new AbortController();
  vi.spyOn(AbortSignal,'timeout').mockReturnValue(timeout.signal);
  const caller=new AbortController();
  vi.stubGlobal('fetch',vi.fn((_url,init)=>new Promise((_resolve,reject)=>init.signal.addEventListener('abort',()=>reject(init.signal.reason)))));
  const result=researchJson('/fixture',{signal:caller.signal});
  timeout.abort(new DOMException('Request timed out','TimeoutError'));
  await expect(result).rejects.toMatchObject({name:'TimeoutError'});
  expect(AbortSignal.timeout).toHaveBeenCalledWith(20000);
});
