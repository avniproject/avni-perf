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

    // No defaults. These pin which environment you authenticate against, and a default here means a
    // run silently targets whatever environment was hardcoded rather than the one under test.
    // Only read under AUTH_MODE=cognito.
    public static String clientId = required("COGNITO_CLIENT_ID");
    public static String userPoolId = required("COGNITO_USER_POOL_ID");

    private static String required(String property) {
        String value = System.getProperty(property);
        if (value == null || value.isEmpty()) {
            throw new IllegalStateException(
                property + " must be set when running with AUTH_MODE=cognito, e.g. -D" + property + "=...");
        }
        return value;
    }

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

        } catch (CognitoIdentityProviderException e) {
            // Fail this user, not the whole run. System.exit here would discard every result
            // collected so far because one user could not authenticate.
            throw new IllegalStateException(
                "Cognito authentication failed for a user: " + e.awsErrorDetails().errorMessage(), e);
        }
    }
}
