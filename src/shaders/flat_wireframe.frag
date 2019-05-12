#version 330 core

uniform struct LightInfo {
    vec4 position;
    vec3 intensity;
} light;

uniform struct LineInfo {
    float width;
    vec4 color;
} line;

uniform vec3 flat_color; 
uniform float face_enable;

in WireframeVertex {
    vec3 position;
    flat vec3 normal;
    noperspective vec4 edgeA;
    noperspective vec4 edgeB;
    flat int configuration;
} fs_in;

out vec4 fragColor;

vec4 shadeLine( const in vec4 color )
{
    // Find the smallest distance between the fragment and a triangle edge
    float d;
    if ( fs_in.configuration == 0 )
    {
        // Common configuration
        d = min( fs_in.edgeA.x, fs_in.edgeA.y );
        d = min( d, fs_in.edgeA.z );
    }
    else
    {
        // Handle configuration where screen space projection breaks down
        // Compute and compare the squared distances
        vec2 AF = gl_FragCoord.xy - fs_in.edgeA.xy;
        float sqAF = dot( AF, AF );
        float AFcosA = dot( AF, fs_in.edgeA.zw );
        d = abs( sqAF - AFcosA * AFcosA );

        vec2 BF = gl_FragCoord.xy - fs_in.edgeB.xy;
        float sqBF = dot( BF, BF );
        float BFcosB = dot( BF, fs_in.edgeB.zw );
        d = min( d, abs( sqBF - BFcosB * BFcosB ) );

        // Only need to care about the 3rd edge for some configurations.
        if ( fs_in.configuration == 1 || fs_in.configuration == 2 || fs_in.configuration == 4 )
        {
            float AFcosA0 = dot( AF, normalize( fs_in.edgeB.xy - fs_in.edgeA.xy ) );
            d = min( d, abs( sqAF - AFcosA0 * AFcosA0 ) );
        }

        d = sqrt( d );
    }

    // Blend between line color and phong color
    float mixVal;
    if ( d < line.width - 1.0 )
    {
        mixVal = 1.0;
    }
    else if ( d > line.width + 1.0 )
    {
        mixVal = 0.0;
    }
    else
    {
        float x = d - ( line.width - 1.0 );
        mixVal = exp2( -2.0 * ( x * x ) );
    }

    return mix( color, line.color, mixVal );
}

void main()
{
    //vec4 color = vec4( goochModel( fs_in.position, normalize( fs_in.normal ) ), alpha );
    //vec4 color = vec4( flat_color.x, flat_color.y, flat_color.z, alpha );
    
    vec4 color = vec4( flat_color, face_enable );
    fragColor = shadeLine( color );
}
