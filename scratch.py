import sys
import Quartz
import Vision
from Foundation import NSURL

def extract_text(image_path):
    url = NSURL.fileURLWithPath_(image_path)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
    
    requests = []
    text_result = []
    
    def handle_result(request, error):
        for observation in request.results():
            for candidate in observation.topCandidates_(1):
                text_result.append(candidate.string())

    request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handle_result)
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    
    handler.performRequests_error_([request], None)
    
    return "\n".join(text_result)

print(extract_text(sys.argv[1]))
