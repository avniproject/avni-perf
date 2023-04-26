package org.avni.helper;

import software.amazon.awssdk.awscore.defaultsmode.DefaultsMode;
import software.amazon.awssdk.services.cognitoidentityprovider.CognitoIdentityProviderClient;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AdminInitiateAuthRequest;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AdminInitiateAuthResponse;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AuthFlowType;
import software.amazon.awssdk.services.cognitoidentityprovider.model.CognitoIdentityProviderException;

import java.util.HashMap;
import java.util.Map;

public class CognitoHelper {

    public static String clientId = System.getProperty("COGNITO_CLIENT_ID", "6c3qo1sple00feq8mbpum1duit");
    public static String userPoolId = System.getProperty("COGNITO_USER_POOL_ID","ap-south-1_UdXEEi1qP");

    public static String getTokenForUser(String userName, String password) {
//        System.out.println("Getting token for: " + userName + "/" + password);
        AdminInitiateAuthResponse authResponse = initiateAuth(CognitoIdentityProviderClient.builder().defaultsMode(DefaultsMode.AUTO).build(), userName, password);
//        System.out.println("Result Challenge is : " + authResponse.challengeName() );
//        System.out.println("Result idToken is : " + authResponse.authenticationResult().idToken());
        return authResponse.authenticationResult().idToken();
    }

    public static AdminInitiateAuthResponse initiateAuth(CognitoIdentityProviderClient identityProviderClient, String userName, String password) {
        try {
            Map<String,String> authParameters = new HashMap<>();
            authParameters.put("USERNAME", userName);
            authParameters.put("PASSWORD", password);

            AdminInitiateAuthRequest authRequest = AdminInitiateAuthRequest.builder()
                .clientId(clientId)
                .userPoolId(userPoolId)
                .authParameters(authParameters)
                .authFlow(AuthFlowType.ADMIN_USER_PASSWORD_AUTH)
                .build();

            return identityProviderClient.adminInitiateAuth(authRequest);

        } catch(CognitoIdentityProviderException e) {
            System.err.println(e.awsErrorDetails().errorMessage());
            System.exit(1);
        }

        return null;
    }
}
