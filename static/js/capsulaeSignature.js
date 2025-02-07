function timedDetect() 
{
  if (wgssSignatureSDK.running) 
  {
  } 
  else 
  {
  }
}
var timeout = setTimeout(timedDetect, 1500);
  
function onDetectRunning()
{
  clearTimeout(timeout);
}
// pass the starting service port  number as configured in the registry
var wgssSignatureSDK = new WacomGSS_SignatureSDK(onDetectRunning, 8000)

function restartSession(onRestartSession)
{
  wgssSignatureSDK = new WacomGSS_SignatureSDK(onRestartSession, 8000)
}

function captureSignature(canvas, input, name, description) {
  var sigObj;
  var sigCtl;
  var dynCapt;
  var ctx ;
  
  function onPutSigData(sigObjV, status)
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status) {}
    else {}
  }
  
  function onGetSigText(sigObjV, data, status)
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status)
    {
	  console.log(canvas.toDataURL());
	  input.value = canvas.toDataURL();
      var vData = new wgssSignatureSDK.Variant();
      vData.type = wgssSignatureSDK.VariantType.VARIANT_BASE64;
      vData.base64 = data;
      sigObjV.PutSigData(vData, onPutSigData);
    }
    else {}
  }
  
  function onGetAdditionalData(sigObjV, additionalData, status)
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status)
    {
      sigObjV.GetSigText(onGetSigText);
    }
    else {}
  }
  
  function onRenderBitmap(sigObjV, bmpObj, status) 
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status) 
    {
      if(bmpObj.isBase64) {}
      else {}
      ctx.drawImage(bmpObj.image, 0, 0);
      sigObjV.GetAdditionalData(wgssSignatureSDK.CaptData.CaptMachineOS, onGetAdditionalData);
	  
    } 
    else {}
  }
  
  function onPutExtraData(sigObjV, status) 
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status) 
    {
      var flags = wgssSignatureSDK.RBFlags.RenderOutputPicture |
                  wgssSignatureSDK.RBFlags.RenderColor24BPP;
      sigObjV.RenderBitmap("bmp", canvas.width, canvas.height, 0.7, 0x00000000, 0x00FFFFFF, flags, 0, 0, onRenderBitmap);
      this.sigObj = sigObjV;
    } 
    else {}
  }
  
  function onDynCaptCapture(dynCaptV, sigObjV, status)
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status)
    {
      sigObjV.PutExtraData("extra key", "extra value", onPutExtraData);
    } 
    else if(1 == status) {} 
    else {}  
  }
        
  function onSigCtlPutLicence(sigCtlV, status)
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status)
    {
      dynCapt.Capture(sigCtlV, name, description, null, null, onDynCaptCapture);
    }
    else {}
  }  

  function onSigCtlConstructor(sigCtlV, status)
  {
     if(wgssSignatureSDK.ResponseStatus.OK == status)
     {
        sigCtlV.PutLicence(LICENCEKEY, onSigCtlPutLicence);
     }
     else {}
  }
  
  function onDynCaptConstructor(dynCaptV, status) 
  {
    if(wgssSignatureSDK.ResponseStatus.OK == status)
    {
      this.sigCtl = new wgssSignatureSDK.SigCtl(onSigCtlConstructor);
    }
    else
    {
      if(wgssSignatureSDK.ResponseStatus.INVALID_SESSION == status)
      {
        restartSession(captureSignature);
      }
    }
  }
            
  if (wgssSignatureSDK.running) 
  {
    ctx = canvas.getContext("2d");
    dynCapt = new wgssSignatureSDK.DynamicCapture(onDynCaptConstructor);
  }
}



$(document).ready(()=>{
    $("body").on("click", ".sign-capture-btn", function(e){
        e.preventDefault(); 
        e.stopPropagation();
        let name = $(this).data("name");
        let target = $(this).data("target");
        let input = $(this).data("input");
        let description = "Consentimiento informado para registro y tratamiento de datos en Capsulae.org";
        captureSignature(target, input, name, description);
    });
});

/*document.querySelectorAll(".sign-capture-btn").forEach( (element)=>{

		element.addEventListener("click", function(e){
		e.preventDefault(); e.stopPropagation();
		let name = element.dataset.name;
		let target = document.querySelector(element.dataset.target);
		let input = document.querySelector(element.dataset.input);
		let description = "Consentimiento informado para registro y tratamiento de datos en Capsulae.org";
		captureSignature(target, input, name, description);
	});
});*/

