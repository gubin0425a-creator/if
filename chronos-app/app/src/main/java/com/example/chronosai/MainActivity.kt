package com.example.chronosai

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.content.Context
import android.os.Bundle
import android.webkit.JsResult
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.example.chronosai.theme.ChronosAITheme

class MainActivity : ComponentActivity() {

    private val PREFS_NAME = "chronos_settings"
    private val KEY_IP = "server_ip"
    private val KEY_PORT = "server_port"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val sharedPref = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

        // 동일 와이파이 / 유선 USB 연결 시 설정을 원클릭으로 주입하기 위한 인텐트 처리
        intent?.let {
            val ipExtra = it.getStringExtra("ip")
            val portExtra = it.getStringExtra("port")
            val codeExtra = it.getStringExtra("master_code")
            
            val editor = sharedPref.edit()
            var changed = false
            if (!ipExtra.isNullOrEmpty()) {
                editor.putString(KEY_IP, ipExtra)
                changed = true
            }
            if (!portExtra.isNullOrEmpty()) {
                editor.putString(KEY_PORT, portExtra)
                changed = true
            }
            if (!codeExtra.isNullOrEmpty()) {
                editor.putString("master_code", codeExtra)
                changed = true
            }
            if (changed) {
                editor.apply()
            }
        }

        val initialIp = sharedPref.getString(KEY_IP, "192.168.0.162") ?: "192.168.0.162"
        val initialPort = sharedPref.getString(KEY_PORT, "5000") ?: "5000"

        setContent {
            ChronosAITheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF1E1E2E) // Matching Catppuccin Mocha Dark theme background
                ) {
                    ChronosAppContent(
                        context = this,
                        initialIp = initialIp,
                        initialPort = initialPort,
                        saveSettings = { ip, port ->
                            sharedPref.edit().apply {
                                putString(KEY_IP, ip)
                                putString(KEY_PORT, port)
                                apply()
                            }
                        }
                    )
                }
            }
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChronosAppContent(
    context: Context,
    initialIp: String,
    initialPort: String,
    saveSettings: (String, String) -> Unit
) {
    var ip by remember { mutableStateOf(initialIp) }
    var port by remember { mutableStateOf(initialPort) }
    var webViewInstance by remember { mutableStateOf<WebView?>(null) }
    
    var isLoading by remember { mutableStateOf(true) }
    var loadingProgress by remember { mutableStateOf(0) }
    var hasError by remember { mutableStateOf(false) }
    var triggerReload by remember { mutableStateOf(0) }

    val currentUrl = remember(ip, port, triggerReload) {
        "http://$ip:$port/mobile"
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF1E1E2E))
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        if (!hasError) {
            AndroidView(
                factory = { ctx ->
                    WebView(ctx).apply {
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = true
                        settings.loadWithOverviewMode = true
                        settings.useWideViewPort = true
                        
                        class WebAppInterface {
                            @android.webkit.JavascriptInterface
                            fun saveMasterCode(code: String) {
                                val sharedPref = context.getSharedPreferences("chronos_settings", Context.MODE_PRIVATE)
                                sharedPref.edit().putString("master_code", code).apply()
                            }

                            @android.webkit.JavascriptInterface
                            fun savePhoneRecord(recordJson: String) {
                                try {
                                    val file = java.io.File(context.filesDir, "chronos_generation_records.json")
                                    val existingData = if (file.exists()) file.readText() else "[]"
                                    val jsonArray = org.json.JSONArray(existingData)
                                    val newRecord = org.json.JSONObject(recordJson)
                                    jsonArray.put(newRecord)
                                    file.writeText(jsonArray.toString(2))
                                } catch (e: Exception) {
                                    e.printStackTrace()
                                }
                            }

                            @android.webkit.JavascriptInterface
                            fun getPhoneRecords(): String {
                                return try {
                                    val file = java.io.File(context.filesDir, "chronos_generation_records.json")
                                    if (file.exists()) file.readText() else "[]"
                                } catch (e: Exception) {
                                    "[]"
                                }
                            }
                        }
                        addJavascriptInterface(WebAppInterface(), "AndroidBridge")
                        
                        webViewClient = object : WebViewClient() {
                            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                                super.onPageStarted(view, url, favicon)
                                isLoading = true
                                hasError = false
                            }

                            override fun onPageFinished(view: WebView?, url: String?) {
                                super.onPageFinished(view, url)
                                isLoading = false
                                
                                // Auto-inject the persisted master code from native preferences
                                val sharedPref = context.getSharedPreferences("chronos_settings", Context.MODE_PRIVATE)
                                val savedMasterCode = sharedPref.getString("master_code", "") ?: ""
                                if (savedMasterCode.isNotEmpty()) {
                                    view?.evaluateJavascript("javascript:if(typeof injectSavedMasterCode === 'function') { injectSavedMasterCode('$savedMasterCode'); }", null)
                                }
                            }

                            override fun onReceivedError(
                                view: WebView?,
                                request: WebResourceRequest?,
                                error: WebResourceError?
                            ) {
                                if (request?.isForMainFrame == true) {
                                    hasError = true
                                    isLoading = false
                                }
                            }
                        }

                        webChromeClient = object : WebChromeClient() {
                            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                                super.onProgressChanged(view, newProgress)
                                loadingProgress = newProgress
                            }

                            override fun onJsAlert(
                                view: WebView?,
                                url: String?,
                                message: String?,
                                result: JsResult?
                            ): Boolean {
                                AlertDialog.Builder(context)
                                    .setTitle("chip찮이즘")
                                    .setMessage(message)
                                    .setPositiveButton(android.R.string.ok) { _, _ -> result?.confirm() }
                                    .setCancelable(false)
                                    .create()
                                    .show()
                                return true
                            }

                            override fun onJsConfirm(
                                view: WebView?,
                                url: String?,
                                message: String?,
                                result: JsResult?
                            ): Boolean {
                                AlertDialog.Builder(context)
                                    .setTitle("chip찮이즘")
                                    .setMessage(message)
                                    .setPositiveButton(android.R.string.ok) { _, _ -> result?.confirm() }
                                    .setNegativeButton(android.R.string.cancel) { _, _ -> result?.cancel() }
                                    .setCancelable(false)
                                    .create()
                                    .show()
                                return true
                            }
                        }
                        
                        loadUrl(currentUrl)
                        webViewInstance = this
                    }
                },
                update = { webView ->
                    // When IP or Port changes, reload the URL
                    if (webView.url != currentUrl) {
                        webView.loadUrl(currentUrl)
                    }
                },
                modifier = Modifier.fillMaxSize()
            )

            // Progress bar at the top
            if (isLoading) {
                LinearProgressIndicator(
                    progress = { loadingProgress / 100f },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp),
                    color = Color(0xFF89B4FA),
                    trackColor = Color(0xFF313244)
                )
            }
        } else {
            // Connection error / settings UI
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "🔌 Chronos Server Offline",
                    color = Color(0xFFF38BA8),
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                
                Text(
                    text = "PC 서버가 활성화되어 있고, 스마트폰과 동일한 와이파이(네트워크)에 연결되어 있는지 확인해 주세요.",
                    color = Color(0xFFA6ADC8),
                    fontSize = 14.sp,
                    modifier = Modifier.padding(bottom = 32.dp),
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF181825)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "서버 IP 주소 설정",
                            color = Color(0xFF89B4FA),
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(bottom = 12.dp)
                        )

                        OutlinedTextField(
                            value = ip,
                            onValueChange = { ip = it },
                            label = { Text("PC IP 주소") },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedBorderColor = Color(0xFF89B4FA),
                                unfocusedBorderColor = Color(0xFF313244),
                                focusedLabelColor = Color(0xFF89B4FA),
                                unfocusedLabelColor = Color(0xFFA6ADC8)
                            ),
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        OutlinedTextField(
                            value = port,
                            onValueChange = { port = it },
                            label = { Text("포트 (Port)") },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedBorderColor = Color(0xFF89B4FA),
                                unfocusedBorderColor = Color(0xFF313244),
                                focusedLabelColor = Color(0xFF89B4FA),
                                unfocusedLabelColor = Color(0xFFA6ADC8)
                            ),
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )

                        Spacer(modifier = Modifier.height(20.dp))

                        Button(
                            onClick = {
                                saveSettings(ip, port)
                                hasError = false
                                isLoading = true
                                triggerReload++
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF89B4FA)),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text(
                                text = "연결 재시도",
                                color = Color(0xFF1E1E2E),
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }
        }
    }
}

