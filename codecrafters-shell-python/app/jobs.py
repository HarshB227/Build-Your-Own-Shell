from dataclasses import dataclass


@dataclass
class Job:
    id: int
    pid: int
    command: str


BackgroundJobs: dict[int, Job] = {}
next_job_id = 1


def add_job(pid: int, command: str) -> int:
    """Add a background job and return its job ID"""
    global next_job_id
    job_id = next_job_id
    BackgroundJobs[job_id] = Job(id=job_id, pid=pid, command=command)
    next_job_id += 1
    return job_id
