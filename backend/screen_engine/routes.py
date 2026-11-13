from fastapi import APIRouter, HTTPException, Request
from backend.shared.contracts import CaptureRequest, ScreenResponse

router = APIRouter(prefix="/api/screen", tags=["screen"])


@router.post("/capture", response_model=ScreenResponse)
async def capture(request: Request, body: CaptureRequest):
    return await request.app.state.coordinate_capture(request, body, False)


@router.post("/analyze", response_model=ScreenResponse)
async def analyze(request: Request, body: CaptureRequest):
    return await request.app.state.coordinate_capture(request, body, True)


@router.get("/latest", response_model=ScreenResponse)
async def latest(request: Request):
    if request.app.state.latest is None:
        raise HTTPException(404, "No successful capture in this backend session")
    return ScreenResponse(observation=request.app.state.latest)
