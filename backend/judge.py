"""C++17 local runner with Windows Job limits and bounded output.

Each compile and execution gets a private directory and a kill-on-close Job.
This is resource isolation, not a filesystem sandbox or an official OJ judge.
"""
import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time

_SIZE=C.c_size_t
_SPAWN_LOCK=threading.Lock()
class _Basic(C.Structure):
    _fields_=[('processTime',C.c_longlong),('jobTime',C.c_longlong),('flags',W.DWORD),('minWS',_SIZE),('maxWS',_SIZE),('active',W.DWORD),('affinity',_SIZE),('priority',W.DWORD),('scheduling',W.DWORD)]
class _IO(C.Structure):
    _fields_=[(name,C.c_ulonglong) for name in ('readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes')]
class _Limits(C.Structure):
    _fields_=[('basic',_Basic),('io',_IO),('processMemory',_SIZE),('jobMemory',_SIZE),('peakProcess',_SIZE),('peakJob',_SIZE)]
class _Associate(C.Structure):
    _fields_=[('key',C.c_void_p),('port',W.HANDLE)]
class _Security(C.Structure):
    _fields_=[('size',W.DWORD),('descriptor',C.c_void_p),('inherit',W.BOOL)]
class _Startup(C.Structure):
    _fields_=[('size',W.DWORD),('reserved',W.LPWSTR),('desktop',W.LPWSTR),('title',W.LPWSTR),('x',W.DWORD),('y',W.DWORD),('cx',W.DWORD),('cy',W.DWORD),('charsX',W.DWORD),('charsY',W.DWORD),('fill',W.DWORD),('flags',W.DWORD),('show',W.WORD),('reservedSize',W.WORD),('reservedPtr',C.c_void_p),('stdin',W.HANDLE),('stdout',W.HANDLE),('stderr',W.HANDLE)]
class _Process(C.Structure):
    _fields_=[('process',W.HANDLE),('thread',W.HANDLE),('pid',W.DWORD),('tid',W.DWORD)]

def _kernel():
    k=C.WinDLL('kernel32',use_last_error=True)
    prototypes={
      'CreateJobObjectW':([C.c_void_p,W.LPCWSTR],W.HANDLE),
      'CreateIoCompletionPort':([W.HANDLE,W.HANDLE,_SIZE,W.DWORD],W.HANDLE),
      'SetInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD],W.BOOL),
      'QueryInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p],W.BOOL),
      'CreateFileW':([W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE],W.HANDLE),
      'CreateProcessW':([W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,C.c_void_p,C.c_void_p],W.BOOL),
      'AssignProcessToJobObject':([W.HANDLE,W.HANDLE],W.BOOL),
      'ResumeThread':([W.HANDLE],W.DWORD),
      'WaitForSingleObject':([W.HANDLE,W.DWORD],W.DWORD),
      'GetExitCodeProcess':([W.HANDLE,C.c_void_p],W.BOOL),
      'GetProcessTimes':([W.HANDLE,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p],W.BOOL),
      'GetQueuedCompletionStatus':([W.HANDLE,C.c_void_p,C.c_void_p,C.c_void_p,W.DWORD],W.BOOL),
      'TerminateJobObject':([W.HANDLE,W.UINT],W.BOOL),
      'TerminateProcess':([W.HANDLE,W.UINT],W.BOOL),
      'SetHandleInformation':([W.HANDLE,W.DWORD,W.DWORD],W.BOOL),
      'CloseHandle':([W.HANDLE],W.BOOL)}
    for name,(args,result) in prototypes.items():getattr(k,name).argtypes=args;getattr(k,name).restype=result
    return k

def _cancelled(cancel):
    return bool(cancel and (cancel.is_set() if hasattr(cancel,'is_set') else cancel()))

def _run(command,inp,directory,time_ms,memory_mb,output_limit=32*1024*1024,cancel=None,max_processes=1):
    if os.name!='nt':raise RuntimeError('此评测器需要 Windows Job Object，未启用无内存保护的降级运行')
    k=_kernel();handles=[];pi=_Process();reason=None;rc=None;elapsed=0;memory=0
    folder=Path(directory);input_path=folder/'stdin';out_path=folder/'stdout';err_path=folder/'stderr'
    input_path.write_bytes(inp.encode('utf-8') if isinstance(inp,str) else inp)
    security=_Security(C.sizeof(_Security),None,True)
    def valid(handle):return handle and handle!=C.c_void_p(-1).value
    def check(value):
        if not value:raise C.WinError(C.get_last_error())
        return value
    def create_file(path,access,creation):
        h=k.CreateFileW(str(path),access,7,C.byref(security),creation,0x80,None)
        if not valid(h):raise C.WinError(C.get_last_error())
        handles.append(h);return h
    try:
        job=check(k.CreateJobObjectW(None,None));handles.append(job)
        port=check(k.CreateIoCompletionPort(W.HANDLE(-1),None,0,1));handles.append(port)
        associated=_Associate(job,port);check(k.SetInformationJobObject(job,7,C.byref(associated),C.sizeof(associated)))
        limits=_Limits();limits.basic.flags=0x2|0x8|0x100|0x200|0x400|0x2000
        limits.basic.processTime=max(1,int(time_ms))*10000;limits.basic.active=max_processes
        limits.processMemory=limits.jobMemory=int(memory_mb)*1024*1024
        check(k.SetInformationJobObject(job,9,C.byref(limits),C.sizeof(limits)))
        startup=_Startup();startup.size=C.sizeof(startup);startup.flags=0x100|1;startup.show=0
        # Concurrent submissions cannot inherit one another's temporary input/output handles.
        with _SPAWN_LOCK:
            startup.stdin=create_file(input_path,0x80000000,3)
            startup.stdout=create_file(out_path,0x40000000,2);startup.stderr=create_file(err_path,0x40000000,2)
            line=C.create_unicode_buffer(subprocess.list2cmdline([str(a) for a in command]))
            try:
                check(k.CreateProcessW(str(command[0]),line,None,None,True,0x4|0x08000000,None,str(folder),C.byref(startup),C.byref(pi)))
                handles.extend([pi.process,pi.thread])
            finally:
                for handle in (startup.stdin,startup.stdout,startup.stderr):
                    if handle:k.SetHandleInformation(handle,1,0)
        # The process cannot execute before limits and completion notifications are attached.
        check(k.AssignProcessToJobObject(job,pi.process))
        if k.ResumeThread(pi.thread)==0xffffffff:raise C.WinError(C.get_last_error())
        started=time.monotonic()
        def notifications():
            nonlocal reason
            message=W.DWORD();key=_SIZE();overlapped=C.c_void_p()
            while k.GetQueuedCompletionStatus(port,C.byref(message),C.byref(key),C.byref(overlapped),0):
                if message.value in (9,10):reason='MLE'
                elif message.value in (1,2) and reason!='MLE':reason='TLE'
        while True:
            done=k.WaitForSingleObject(pi.process,5)==0
            notifications()
            if out_path.stat().st_size+err_path.stat().st_size>output_limit:reason=reason or 'OLE'
            if _cancelled(cancel):reason='ERROR'
            if not done and (time.monotonic()-started)*1000>time_ms:reason=reason or 'TLE'
            if reason and not done:k.TerminateJobObject(job,1);k.WaitForSingleObject(pi.process,5000);done=True
            if done:break
        # Drain notifications after process termination; memory denial is not inferred from stderr.
        for _ in range(3):notifications();time.sleep(.002)
        code=W.DWORD();check(k.GetExitCodeProcess(pi.process,C.byref(code)));rc=code.value
        timing=[C.c_ulonglong() for _ in range(4)]
        if k.GetProcessTimes(pi.process,*[C.byref(v) for v in timing]):elapsed=(timing[2].value+timing[3].value)/10000
        measured=_Limits()
        if k.QueryInformationJobObject(job,9,C.byref(measured),C.sizeof(measured),None):memory=measured.peakProcess//1024
    finally:
        if pi.process:
            # Covers failures between CreateProcess and assignment, as well as abandoned work.
            if k.WaitForSingleObject(pi.process,0)!=0:k.TerminateProcess(pi.process,1);k.WaitForSingleObject(pi.process,5000)
        for handle in reversed(handles):k.CloseHandle(handle)
    with out_path.open('rb') as stream:output=stream.read(output_limit).decode('utf-8','replace')
    with err_path.open('rb') as stream:stderr=stream.read(min(output_limit,65536)).decode('utf-8','replace')
    return {'verdict':reason or ('RE' if rc else None),'timeMs':round(elapsed,2),'memoryKb':memory,'output':output,'stderr':stderr,'returncode':rc}

class Judge:
    def __init__(self,assets,work_dir):
        self.assets=assets;self.work_dir=Path(work_dir);self.work_dir.mkdir(parents=True,exist_ok=True)
        bundled=__import__('paths').ROOT/'compiler'/'ucrt64'/'bin'/'g++.exe'
        self.compiler=str(bundled) if bundled.is_file() else shutil.which('g++')

    def execute(self,identity,code,mode='submit',input_text='',cancel=None,sample_run=None):
        result={'verdict':'ERROR','scope':'samples','timeMs':None,'memoryKb':None,'passed':0,'total':0,'output':'','stderr':'','message':'','caseResults':[]}
        try:
            bundle=self.assets.bundle(identity);result['scope']=bundle['scope']
            if mode not in ('run','submit'):raise ValueError('运行模式无效')
            if not isinstance(code,str) or not code.strip():raise ValueError('请先输入 C++17 代码')
            if len(code.encode('utf-8'))>262144:raise ValueError('代码超过 256 KiB')
            if not self.compiler:raise RuntimeError('没有找到本机 C++17 编译器')
            sample_run=(not input_text) if sample_run is None else sample_run
            if mode=='run' and sample_run:
                if hasattr(self.assets,'problem'):
                    cases=[{'name':case.get('name',f'样例 {i+1}'),'input':case['input'],'output':case['output']} for i,case in enumerate(self.assets.problem(identity).get('samples',[]))]
                else:cases=bundle['cases']
            else:cases=[{'name':'自定义输入','input':input_text,'output':None}] if mode=='run' else bundle['cases']
            result['total']=len(cases)
            if not cases:raise ValueError('此题没有可用测试样例，请先补充原题资产')
            if _cancelled(cancel):raise ValueError('评测已取消')
            with tempfile.TemporaryDirectory(prefix='submission-',dir=self.work_dir) as temporary:
                directory=Path(temporary);source=directory/'main.cpp';exe=directory/'main.exe';source.write_text(code,encoding='utf-8')
                compiled=_run([self.compiler,'-O2','-std=c++17','-o',exe,source],'',directory,30000,1024,262144,cancel,max_processes=32)
                if compiled['verdict']:
                    result.update(verdict='ERROR' if _cancelled(cancel) else 'CE',stderr=compiled['stderr'],message='编译已取消' if _cancelled(cancel) else 'C++17 编译未通过');return result
                maximum_time=maximum_memory=0;failed=None
                for index,case in enumerate(cases):
                    ran=_run([exe],case['input'],directory,bundle['limits']['timeMs'],bundle['limits']['memoryMb'],cancel=cancel)
                    maximum_time=max(maximum_time,ran['timeMs']);maximum_memory=max(maximum_memory,ran['memoryKb'])
                    result.update(timeMs=maximum_time,memoryKb=maximum_memory,output=ran['output'][:65536],stderr=ran['stderr'])
                    verdict=ran['verdict'];message=''
                    if not verdict and case['output'] is not None:
                        checker=bundle.get('checker')
                        got,expected=ran['output'],case['output']
                        if bundle.get('caseInsensitive'):got,expected=got.lower(),expected.lower()
                        okay=bool(checker(case['input'],ran['output'],case['output'])) if checker else got.split()==expected.split()
                        if not okay:
                            verdict='ERROR' if bundle.get('nonunique') and not checker else 'WA'
                            message='多解题尚未配备审核判定器，无法自动验证此输出' if verdict=='ERROR' else '实际输出与期望不符'
                    verdict=verdict or ('RUN_OK' if case['output'] is None else 'SAMPLE_PASS')
                    public=mode=='run' or bundle['scope']=='samples'
                    result['caseResults'].append({'name':str(case.get('name') or f'测试 {index+1}') if public else f'审核测试 {index+1}',
                      'input':str(case['input'])[:65536] if public else '', 'expected':str(case['output'])[:65536] if public and case['output'] is not None else None,
                      'actual':ran['output'][:65536] if public else '', 'verdict':verdict,'timeMs':ran['timeMs'],'exitCode':ran['returncode'],'message':message})
                    if verdict=='SAMPLE_PASS':result['passed']+=1
                    elif verdict!='RUN_OK':failed=failed or verdict
                    if ran['verdict'] or failed and mode=='submit':
                        result.update(verdict=failed,message=message or f'测试 {index+1}/{len(cases)}：{failed}');return result
                custom=mode=='run' and not sample_run
                result.update(verdict=failed or ('RUN_OK' if custom else 'SAMPLE_PASS' if mode=='run' or bundle['scope']=='samples' else 'AC'),
                  message='部分样例输出与期望不符' if failed else '自定义输入运行完成；没有期望输出，不判断正确性' if custom else '官方样例全部通过；尚未验证完整正确性' if mode=='run' or bundle['scope']=='samples' else '本地审核测试全部通过；不是原 OJ 判定')
                return result
        except Exception as error:
            result.update(verdict='ERROR',message=str(error));return result
